#!/usr/bin/env python3
import tkinter.messagebox
import tkinter as tk
from tkinter import font
from functools import partial
from tksheet import Sheet
import os
import ast
import threading

from config import Config
from impartus import Impartus
from utils import Utils


class App:
    def __init__(self):
        # ui elements
        self.user_box = None
        self.pass_box = None
        self.url_box = None
        self.show_videos_button = None

        # element groups
        self.frame_auth = None
        self.frame_toolbar = None
        self.frame_content = None

        # content table
        self.sheet = None

        # sort options
        self.sort_by = None
        self.sort_order = None

        self.threads = list()

        # root container
        self.app = None

        # backend
        self.impartus = None

        # fields
        self.columns = None

        # configs
        self.conf = Config.load('yaml.conf')
        self.colorscheme_config = Config.load('color-schemes.conf')
        self.colorscheme = self.colorscheme_config.get(self.colorscheme_config.get('default'))
        self.colorscheme_buttons = list()
        self.color_var = None

        self._init_backend()
        self._init_ui()

    def _init_backend(self):
        """
        backend initialization.
        """
        self.impartus = Impartus()
        self.conf = Config.load()

        self.columns = {k: v for k, v in enumerate([
            # data fields
            {'name': 'Subject', 'show': True, 'type': 'data', 'mapping': 'subjectNameShort', 'title_case': False,
             'sortable': True, 'header': 'Subject'},
            {'name': 'Lecture #', 'show': True, 'type': 'data', 'mapping': 'seqNo', 'title_case': False,
             'sortable': True, 'header': 'Lecture #'},
            {'name': 'Professor', 'show': True, 'type': 'data', 'mapping': 'professorName_raw', 'title_case': True,
             'sortable': True, 'header': 'Professor'},
            {'name': 'Topic', 'show': True, 'type': 'data', 'mapping': 'topic_raw', 'title_case': True,
             'sortable': True, 'header': 'Topic'},
            {'name': 'Duration', 'show': True, 'type': 'data', 'mapping': 'actualDurationReadable', 'title_case': False,
             'sortable': True, 'header': 'Duration'},
            {'name': 'Tracks', 'show': True, 'type': 'data', 'mapping': 'tapNToggle', 'title_case': False,
             'sortable': True, 'header': 'Tracks'},
            {'name': 'Date', 'show': True, 'type': 'data', 'mapping': 'startDate', 'title_case': False,
             'sortable': True, 'header': 'Date'},
            # progress bar
            {'name': 'Downloaded?', 'show': True, 'type': 'progressbar', 'title_case': False, 'sortable': True,
             'header': 'Downloaded?'},
            # buttons
            {'name': 'Download Video', 'show': True, 'type': 'button', 'function': self.download_video,
             'sortable': False, 'text': '⬇', 'header': 'Video'},
            {'name': 'Open Folder', 'show': True, 'type': 'button', 'function': self.open_folder,
             'sortable': False, 'text': '⏏', 'header': 'Folder'},
            {'name': 'Play Video', 'show': True, 'type': 'button', 'function': self.play_video,
             'sortable': False, 'text': '▶', 'header': 'Video'},
            {'name': 'Download Slides', 'show': True, 'type': 'button', 'function': self.download_slides,
             'sortable': False, 'text': '⬇', 'header': 'Slides'},
            {'name': 'Show Slides', 'show': True, 'type': 'button', 'function': self.show_slides,
             'sortable': False, 'text': '▤', 'header':  'Slides'},
            {'name': 'download_video_state', 'show': False, 'type': 'state', 'header': 'download_video_state'},
            {'name': 'open_folder_state', 'show': False, 'type': 'state', 'header': 'open_folder_state'},
            {'name': 'play_video_state', 'show': False, 'type': 'state', 'header': 'play_slides_state'},
            {'name': 'download_slides_state', 'show': False, 'type': 'state', 'header': 'download_slides_state'},
            {'name': 'show_slides_state', 'show': False, 'type': 'state', 'header': 'show_slides_state'},
            # index
            {'name': 'Index', 'show': False, 'type': 'auto', 'header': 'Index'},
            # video / slides data
            {'name': 'metadata', 'show': False, 'type': 'metadata', 'header': 'metadata'},
        ])}
        self.headers = [x['header'] for x in self.columns.values()]
        self.names = [x['name'] for x in self.columns.values()]

    def _init_ui(self):
        """
        UI initialization.
        """
        self.app = tkinter.Tk()

        pad = 3
        self.screen_width = self.app.winfo_screenwidth() - pad
        self.screen_height = self.app.winfo_screenheight() - pad
        geometry = '{}x{}+0+0'.format(self.screen_width, self.screen_height)
        self.app.geometry(geometry)
        self.app.title('Impartus Downloader')
        self.app.rowconfigure(0, weight=0)
        self.app.rowconfigure(1, weight=1)
        self.app.columnconfigure(0, weight=1)

        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(family=self.conf.get('content_font'), size=14)
        text_font = font.nametofont("TkTextFont")
        text_font.configure(family=self.conf.get('content_font'), size=14)

        self.add_authentication_form(self.app)
        self.add_toolbar(self.app)
        self.add_content_frame(self.app)
        self.app.rowconfigure(0, weight=0)
        self.app.rowconfigure(1, weight=0)
        self.app.rowconfigure(2, weight=1)

        self.set_color_scheme(self.colorscheme)
        self.app.mainloop()

    def add_authentication_form(self, anchor):
        """
        Adds authentication widgets and blank frame for holding video/lectures data.
        """
        cs = self.colorscheme
        label_options = {
            'padx': 5,
            'pady': 5,
            'sticky': 'ew',
        }
        entry_options = {
            'padx': 5,
            'pady': 5,
        }

        frame_auth = tk.Frame(anchor, padx=0, pady=0)
        frame_auth.grid(row=0, column=0)
        self.frame_auth = frame_auth

        # URL Label and Entry box.
        self.url_label = tk.Label(frame_auth, text='URL')
        self.url_label.grid(row=0, column=0, **label_options)
        self.url_box = tk.Entry(frame_auth, width=30)
        self.url_box.insert(tk.END, self.conf.get('impartus_url'))
        self.url_box.grid(row=0, column=1, **entry_options)

        # Login Id Label and Entry box.
        self.user_label = tk.Label(frame_auth, text='Login (email) ')
        self.user_label.grid(row=1, column=0, **label_options)
        self.user_box = tk.Entry(frame_auth, width=30)
        self.user_box.insert(tk.END, self.conf.get('login_email'))
        self.user_box.grid(row=1, column=1, **entry_options)

        self.pass_label = tk.Label(frame_auth, text='Password ')
        self.pass_label.grid(row=2, column=0, **label_options)
        self.pass_box = tk.Entry(frame_auth, text='', show="*", width=30)
        self.pass_box.bind("<Return>", self.get_videos)
        self.pass_box.grid(row=2, column=1, **entry_options)

        self.show_videos_button = tk.Button(frame_auth, text='Show Videos', command=self.get_videos)
        self.show_videos_button.grid(row=2, column=2)

        # set focus to user entry if it is empty, else to password box.
        if self.user_box.get() == '':
            self.user_box.focus()
        else:
            self.pass_box.focus()

    def add_toolbar(self, anchor):
        button_options = {
            'borderwidth': 0
        }
        grid_options = {
            'padx': 0, 'pady': 0, 'ipadx': 0, 'ipady': 0,
        }
        self.frame_toolbar = tk.Frame(anchor, padx=0, pady=0)

        refresh_button = tk.Button(self.frame_toolbar, text='Refresh ⟳', **button_options)
        refresh_button.grid(row=0, column=1, **grid_options)

        display_columns_button = tk.Button(self.frame_toolbar, text='Columns ▼', **button_options)
        display_columns_button.grid(row=0, column=2, **grid_options)

        add_offline_slides_button = tk.Button(self.frame_toolbar, text='Slides +', **button_options)
        add_offline_slides_button.grid(row=0, column=3, **grid_options)

        subject_edit_button = tk.Button(self.frame_toolbar, text='Subject ✎', **button_options)
        subject_edit_button.grid(row=0, column=4, **grid_options)

        path_edit_button = tk.Button(self.frame_toolbar, text='Video/Slides Location  ✎', **button_options)
        path_edit_button.grid(row=0, column=5, **grid_options)

        # empty column, to keep columns 1-5 centered
        self.frame_toolbar.columnconfigure(0, weight=1)
        # move the color scheme buttons to extreme right
        self.frame_toolbar.columnconfigure(6, weight=1)

        color_var = tk.IntVar()
        self.color_var = color_var
        i = 0
        for k in self.colorscheme_config.keys():
            # skip non-dict keys, skip nested keys
            if type(self.colorscheme_config[k]) == dict and '.' not in k:
                colorscheme_button = tk.Radiobutton(
                    self.frame_toolbar, var=color_var, value=i, bg=self.colorscheme_config[k].get('theme_color'),
                    command=partial(self.set_color_scheme, self.colorscheme_config[k])
                )
                colorscheme_button.grid(row=0, column=6+i, **grid_options, sticky='e')
                self.colorscheme_buttons.append(colorscheme_button)

                # Set the radio button to indicate currently active color scheme.
                if self.colorscheme_config.get('default') == k:
                    self.color_var.set(i)
                i += 1

    def set_color_scheme(self, colorscheme):
        self.colorscheme = colorscheme

        print('setting color scheme: {}'.format(colorscheme))
        cs = colorscheme
        self.app.config(bg=cs['root']['bg'])
        self.frame_auth.configure(bg=cs['root']['bg'])
        self.frame_content.configure(bg=cs['root']['bg'])
        self.frame_toolbar.configure(bg=cs['root']['bg'])

        color_options = {
            'fg': cs['root']['fg'],
            'bg': cs['root']['bg'],
        }
        self.url_label.configure(**color_options)
        self.url_box.configure(**color_options)
        self.user_label.configure(**color_options)
        self.user_box.configure(**color_options)
        self.pass_label.configure(**color_options)
        self.pass_box.configure(**color_options)

        if self.sheet:
            self.sheet.set_options(
                frame_bg=cs['table']['bg'],
                table_bg=cs['table']['bg'],
                table_fg=cs['table']['fg'],
                header_bg=cs['header']['bg'],
                header_fg=cs['header']['fg'],
                header_grid_fg=cs['table']['grid'],
                index_grid_fg=cs['table']['grid'],
                header_border_fg=cs['table']['grid'],
                index_border_fg=cs['table']['grid'],
                table_grid_fg=cs['table']['grid'],
                top_left_bg=cs['header']['bg'],
                top_left_fg=cs['header']['bg']
            )

            self.odd_even_color()
            self.progress_bar_color(redraw=False)
            self.set_button_status()
            self.sheet.refresh()

    def add_content_frame(self, anchor):
        cs = self.colorscheme
        frame_content = tk.Frame(anchor, padx=0, pady=0)
        frame_content.grid(row=2, column=0, sticky='nsew')
        self.frame_content = frame_content

    def get_videos(self, event=None):  # noqa
        """
        Callback function for 'Show Videos' button.
        Fetch video/lectures available to the user and display on the UI.
        """

        self.show_videos_button.config(state='disabled')
        username = self.user_box.get()
        password = self.pass_box.get()
        root_url = self.url_box.get()
        if username == '' or password == '' or root_url == '':
            return

        if not self.impartus.session:
            success = self.impartus.authenticate(username, password, root_url)
            if not success:
                self.impartus.session = None
                tkinter.messagebox.showerror('Error', 'Error authenticating, see console logs for details.')
                self.show_videos_button.config(state='normal')
                return

        subjects = self.impartus.get_subjects(root_url)

        # hide the authentication frame.
        self.frame_auth.grid_forget()

        # show toolbar now.
        self.frame_toolbar.grid(row=1, column=0, sticky='ew')

        # show table of videos under frame_content
        frame = self.frame_content
        self.set_display_widgets(subjects, root_url, frame)


    def sort_table(self, args):
        """
        Sorts the table content.
        """
        col = args[1]
        self.sheet.deselect("all")
        if not self.columns[col].get('sortable'):
            return
        sort_by = self.names[col]
        if sort_by == self.sort_by:
            sort_order = 'asc' if self.sort_order == 'desc' else 'desc'
        else:
            sort_order = 'desc'
        self.sort_by = sort_by
        self.sort_order = sort_order

        reverse = True if sort_order == 'desc' else False

        table_data = self.sheet.get_sheet_data()
        table_data.sort(key=lambda x: x[col], reverse=reverse)

        self.set_headers(sort_by, sort_order)
        self.set_button_status()

    def set_display_widgets(self, subjects, root_url, anchor):
        """
        Create the table/sheet.
        Fill in the data for table content, Set the buttons and their states.
        """
        cs = self.colorscheme

        sheet = Sheet(
            anchor,
            header_font=(self.conf.get("content_font"), 12, "bold"),
            font=(self.conf.get('content_font'), 14, "normal"),
            align='w',
            row_height="1",  # str value for row height in number of lines.
            row_index_align="w",
            auto_resize_default_row_index=False,
            row_index_width=40,
            header_align='center',
            empty_horizontal=0,
            empty_vertical=0,
        )
        self.sheet = sheet

        sheet.enable_bindings((
            "single_select",
            "column_select",
            "column_width_resize",
            "double_click_column_resize",
        ))

        self.set_headers()

        indexes = [x for x, v in self.columns.items() if v['show']]
        sheet.display_columns(indexes=indexes, enable=True)
        anchor.columnconfigure(0, weight=1)
        anchor.rowconfigure(0, weight=1)

        # A mapping dict containing previously downloaded, and possibly moved around / renamed videos.
        # extract their ttid and map those to the correct records, to avoid forcing the user to re-download.
        offline_video_ttid_mapping = self.impartus.get_mkv_ttid_map()
        row = 0
        for subject in subjects:
            videos = self.impartus.get_videos(root_url, subject)
            slides = self.impartus.get_slides(root_url, subject)
            video_slide_mapping = self.impartus.map_slides_to_videos(videos, slides)

            videos = {x['ttid']:  x for x in videos}

            for ttid, video_metadata in videos.items():
                video_metadata = Utils.add_fields(video_metadata, video_slide_mapping)
                video_metadata = Utils.sanitize(video_metadata)

                video_path = self.impartus.get_mkv_path(video_metadata)
                if not os.path.exists(video_path):
                    # or search from the downloaded videos, using video_ttid_map
                    video_path_moved = offline_video_ttid_mapping.get(str(ttid))
                    if video_path_moved:
                        # Use the offline path, if a video found.
                        video_path = video_path_moved

                slides_path = self.impartus.get_slides_path(video_metadata)

                video_exists_on_disk = video_path and os.path.exists(video_path)
                slides_exist_on_server = video_slide_mapping.get(ttid)
                slides_exist_on_disk, slides_path = self.impartus.slides_exist_on_disk(slides_path)

                metadata = {
                    'video_metadata': video_metadata,
                    'video_path': video_path,
                    'video_exists_on_disk': video_exists_on_disk,
                    'slides_exist_on_server': slides_exist_on_server,
                    'slides_exist_on_disk': slides_exist_on_disk,
                    'slides_url': video_slide_mapping.get(ttid),
                    'slides_path': slides_path,
                }
                row_items = list()
                button_states = list()
                for col, item in self.columns.items():
                    text = ''
                    if item['type'] == 'auto':
                        text = row
                    if item['type'] == 'data':
                        text = video_metadata[item['mapping']]
                        # title case
                        text = " ".join(text.splitlines()).strip().title() if item.get('title_case') else text
                    elif item['type'] == 'progressbar':
                        if video_exists_on_disk:
                            text = self.progress_bar_text(100, processed=True)
                        else:
                            text = self.progress_bar_text(0)

                    elif item['type'] == 'button':
                        button_states.append(self.get_button_state(
                            self.names[col], video_exists_on_disk, slides_exist_on_server, slides_exist_on_disk)
                        )
                        text = item.get('text')
                    elif item['type'] == 'state':
                        text = button_states.pop(0)
                    elif item['type'] == 'metadata':
                        text = metadata

                    row_items.append(text)
                sheet.insert_row(values=row_items, idx='end')
                row += 1

        self.reset_column_sizes()
        self.decorate()

        sheet.extra_bindings('column_select', self.sort_table)
        sheet.extra_bindings('cell_select', self.on_click_button_handler)

        # update button status
        self.set_button_status()

        sheet.grid(row=0, column=0, sticky='nsew')

    def set_headers(self, sort_by=None, sort_order=None):
        """
        Set the table headers.
        """
        # set column title to reflect sort status
        headers = self.headers.copy()
        for x, h in enumerate(headers):
            
            if not self.columns[x].get('sortable'):
                continue

            # only sortable headers.
            if h == sort_by:
                sort_icon = '▼' if sort_order == 'desc' else '▲'
            else:
                sort_icon = '⇅'
            headers[x] += ' {}'.format(sort_icon)
        self.sheet.headers(headers)

    def decorate(self):
        """
        calls multiple ui related tweaks.
        """
        self.odd_even_color()
        self.progress_bar_color()

    def progress_bar_color(self, redraw=True):
        """
        Set progress bar color.
        """
        col = self.names.index('Downloaded?')
        num_rows = self.sheet.total_rows()
        cs = self.colorscheme

        for row in range(num_rows):
            odd_even_bg = cs['odd_row']['bg'] if row % 2 else cs['even_row']['bg']
            self.sheet.highlight_cells(
                row, col, fg=cs['progressbar']['fg'], bg=odd_even_bg, redraw=redraw)

    def odd_even_color(self):
        """
        Apply odd/even colors for table for better looking UI.
        """
        cs = self.colorscheme
        num_rows = self.sheet.total_rows()

        self.sheet.highlight_rows(
            list(range(0, num_rows, 2)),
            bg=cs['even_row']['bg'],
            fg=cs['even_row']['fg']
        )
        self.sheet.highlight_rows(
            list(range(1, num_rows, 2)),
            bg=cs['odd_row']['bg'],
            fg=cs['odd_row']['fg']
        )

    def reset_column_sizes(self):
        """
        Adjust column sizes after data has been filled.
        """
        # resize cells
        self.sheet.set_all_column_widths()

        # reset column widths to fill the screen
        pad = 5
        column_widths = self.sheet.get_column_widths()
        table_width = self.sheet.RI.current_width + sum(column_widths) + len(column_widths) + pad
        diff_width = self.frame_content.winfo_width() - table_width

        # adjust extra width only to top N data columns
        n = 2
        data_col_widths = {k: v for k, v in enumerate(column_widths) if self.columns[k]['type'] == 'data'}
        top_n_cols = sorted(data_col_widths, key=data_col_widths.get, reverse=True)[:n]
        for i in top_n_cols:
            self.sheet.column_width(i, column_widths[i] + diff_width // n)

    def set_button_status(self, redraw=False):
        """
        reads the states of the buttons from the hidden state columns, and sets the button states appropriately.
        """
        col_indexes = [x for x, v in enumerate(self.columns.values()) if v['type'] == 'state']
        num_buttons = len(col_indexes)
        for row, row_item in enumerate(self.sheet.get_sheet_data()):
            for col in col_indexes:
                # data set via sheet.insert_row retains tuple/list's element data type,
                # data set via sheet.set_cell_data makes everything a string.
                # Consider everything coming out of a sheet as string to avoid any issues.
                state = str(row_item[col])

                if state == 'True':
                    self.enable_button(row, col - num_buttons, redraw=redraw)
                elif state == 'False':
                    self.disable_button(row, col - num_buttons, redraw=redraw)
        self.sheet.redraw()

    def get_button_state(self, key, video_exists_on_disk, slides_exist_on_server, slides_exist_on_disk):  # noqa
        """
        Checks to identify when certain buttons should be enabled/disabled.
        """
        state = True
        if key == 'Download Video' and video_exists_on_disk:
            state = False
        elif key == 'Open Folder' and not video_exists_on_disk:
            state = False
        elif key == 'Play Video' and not video_exists_on_disk:
            state = False
        elif key == 'Download Slides' and (slides_exist_on_disk or not slides_exist_on_server):
            state = False
        elif key == 'Show Slides' and not slides_exist_on_disk:
            state = False
        return state

    def on_click_button_handler(self, args):
        """
        On click handler for all the buttons, calls the corresponding function as defined by self.columns
        """
        (event, row, col) = args

        # not a button.
        if self.columns[col]['type'] != 'button':
            self.sheet.deselect('all', redraw=True)
            return

        # disabled button
        state_button_col = col + len([x for x, v in self.columns.items() if v['type'] == 'state'])
        state = self.sheet.get_cell_data(row, state_button_col)
        if state == 'False':    # data read from sheet is all string.
            self.sheet.deselect('all', redraw=True)
            return

        # disable the button if it is one of the Download buttons, to prevent a re-download.
        if self.names[col] in ['Download Video', 'Download Slides']:
            self.disable_button(row, col)

        func = self.columns[col]['function']
        func(row, col)

    def disable_button(self, row, col, redraw=True):
        """
        Disable a button given it's row/col position.
        """
        cs = self.colorscheme
        self.sheet.highlight_cells(
            row, col, bg=cs['disabled']['bg'],
            fg=cs['disabled']['fg'],
            redraw=redraw
        )
        # update state field.
        state_button_col = col + len([x for x, v in self.columns.items() if v['type'] == 'state'])
        self.sheet.set_cell_data(row, state_button_col, False, redraw=redraw)

    def enable_button(self, row, col, redraw=True):
        """
        Enable a button given it's row/col position.
        """
        cs = self.colorscheme
        odd_even_bg = cs['odd_row']['bg'] if row % 2 else cs['even_row']['bg']
        odd_even_fg = cs['odd_row']['fg'] if row % 2 else cs['even_row']['fg']
        self.sheet.highlight_cells(row, col, bg=odd_even_bg, fg=odd_even_fg, redraw=redraw)

        # update state field.
        state_button_col = col + len([x for x, v in self.columns.items() if v['type'] == 'state'])
        self.sheet.set_cell_data(row, state_button_col, True, redraw=redraw)

    def get_index(self, row):
        """
        Find the values stored in the hidden column named 'Index', given a row record.
        In case the row value has been updated due to sorting the table, Index field helps identify the new location
        of the associated record.
        """
        # find where is the Index column
        index_col = self.names.index('Index')
        # original row value as per the index column
        return self.sheet.get_cell_data(row, index_col)

    def get_row_after_sort(self, index_value):
        # find the new correct location of the row_index
        col_index = self.names.index('Index')
        col_data = self.sheet.get_column_data(col_index)
        return col_data.index(index_value)

    def progress_bar_text(self, value, processed=False):
        """
        return progress bar text, calls the unicode/ascii implementation.
        """
        if self.conf.get('progress_bar') == 'unicode':
            text = self.progress_bar_text_unicode(value)
        else:
            text = self.progress_bar_text_ascii(value)

        pad = ' ' * 2
        if 0 < value < 100:
            percent_text = '{:2d}%'.format(value)
            status = percent_text
        elif value == 0:
            status = pad + '⃠' + pad
        else:   # 100 %
            if processed:
                status = pad + '✓' + pad
            else:
                status = pad + '⧗' + pad
        return '{} {}{}'.format(text, status, pad)

    def progress_bar_text_ascii(self, value):   # noqa
        """
        progress bar implementation with ascii characters.
        """
        bars = 50
        ascii_space = " "
        if value > 0:
            progress_text = '{}'.format('❘' * (value * bars // 100))
            empty_text = '{}'.format(ascii_space * (bars - len(progress_text)))
            full_text = '{}{} '.format(progress_text, empty_text)
        else:
            full_text = '{}'.format(ascii_space * bars)

        return full_text

    def progress_bar_text_unicode(self, value):    # noqa
        """
        progress bar implementation with unicode blocks.
        """
        chars = ['▏', '▎', '▍', '▌', '▋', '▊', '▉', '█']

        # 1 full unicode block = 8 percent values
        # => 13 unicode blocks needed to represent counter 100.
        unicode_space = ' '
        if value > 0:
            # progress_text: n characters, empty_text: 13-n characters
            progress_text = '{}{}'.format(chars[-1] * (value // 8), chars[value % 8])
            empty_text = '{}'.format(unicode_space * (13-len(progress_text)))
            full_text = '{}{}'.format(progress_text, empty_text)
        else:
            # all 13 unicode whitespace.
            full_text = '{} '.format(unicode_space * 13)
        return full_text

    def progress_bar_callback(self, count, row, col, processed=False):
        """
        Callback function passed to the backend, where it computes the download progress.
        Every time the function is called, it will update the progress bar value.
        """
        updated_row = self.get_row_after_sort(row)
        new_text = self.progress_bar_text(count, processed)
        if new_text != self.sheet.get_cell_data(updated_row, col):
            self.sheet.set_cell_data(updated_row, col, new_text, redraw=True)

    def _download_video(self, video_metadata, filepath, root_url, row, col):
        """
        Download a video in a thread. Update the UI upon completion.
        """

        # create a new Impartus session reusing existing token.
        imp = Impartus(self.impartus.token)
        pb_col = None
        for i, item in enumerate(self.columns.values()):
            if item['type'] == 'progressbar':
                pb_col = i
                break
        # voodoo alert:
        # It is possible for user to sort the table while download is in progress.
        # In such a case, the row index supplied to the function call won't match the row index
        # required to update the correct progressbar/open/play buttons, which now exists at a new
        # location.
        # The hidden column index keeps the initial row index, and remains unchanged.
        # Use row_index to identify the new correct location of the progress bar.
        row_index = self.get_index(row)
        imp.process_video(video_metadata, filepath, root_url, 0,
                          partial(self.progress_bar_callback, row=row_index, col=pb_col))

        # download complete, enable open / play buttons
        updated_row = self.get_row_after_sort(row_index)
        # update progress bar status to complete.
        self.progress_bar_callback(row=row_index, col=pb_col, count=100, processed=True)

        # enable buttons.
        self.enable_button(updated_row, self.names.index('Open Folder'))
        self.enable_button(updated_row, self.names.index('Play Video'))

    def download_video(self, row, col):
        """
        callback function for Download button.
        Creates a thread to download the request video.
        """
        data = self.read_metadata(row)

        video_metadata = data.get('video_metadata')
        filepath = data.get('video_path')
        root_url = self.url_box.get()

        # note: args is a tuple.
        thread = threading.Thread(target=self._download_video, args=(video_metadata, filepath, root_url, row, col,))
        self.threads.append(thread)
        thread.start()

    def _download_slides(self, ttid, file_url, filepath, root_url, row):
        """
        Download a slide doc in a thread. Update the UI upon completion.
        """
        # create a new Impartus session reusing existing token.
        imp = Impartus(self.impartus.token)
        if imp.download_slides(ttid, file_url, filepath, root_url):
            # download complete, enable show slides buttons
            self.enable_button(row, self.names.index('Show Slides'))
        else:
            tkinter.messagebox.showerror('Error', 'Error downloading slides, see console logs for details.')
            self.enable_button(row, self.names.index('Download Slides'))

    def download_slides(self, row, col):
        """
        callback function for Download button.
        Creates a thread to download the request video.
        """
        data = self.read_metadata(row)

        video_metadata = data.get('video_metadata')
        ttid = video_metadata['ttid']
        file_url = data.get('slides_url')
        filepath = data.get('slides_path')
        root_url = self.url_box.get()

        # note: args is a tuple.
        thread = threading.Thread(target=self._download_slides,
                                  args=(ttid, file_url, filepath, root_url, row,))
        self.threads.append(thread)
        thread.start()

    def read_metadata(self, row):
        """
        We saved a hidden column 'metadata' containing metadata for each record.
        Extract it, and eval it as python dict.
        """
        metadata_col = self.names.index('metadata')
        data = self.sheet.get_cell_data(row, metadata_col)
        return ast.literal_eval(data)

    def open_folder(self, row, col):
        """
        fetch video_path's folder from metadata column's cell and open system launcher with it.
        """
        data = self.read_metadata(row)
        video_folder_path = os.path.dirname(data.get('video_path'))
        Utils.open_file(video_folder_path)

    def play_video(self, row, col):
        """
        fetch video_path from metadata column's cell and open system launcher with it.
        """
        data = self.read_metadata(row)
        Utils.open_file(data.get('video_path'))

    def show_slides(self, row, col):
        """
        fetch slides_path from metadata column's cell and open system launcher with it.
        """
        data = self.read_metadata(row)
        Utils.open_file(data.get('slides_path'))


if __name__ == '__main__':
    App()
