import ctypes
import os
import sys
from AppKit import NSApplication, NSImage
from Foundation import NSURL
from io import BytesIO
from datetime import datetime
from functools import partial
import webbrowser

import wx
import wx.adv
import wx.html2
import requests

from icon_processing import IconProcessing
import config_management

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(True)
except:
    pass

class YaffleFrame(wx.Frame):

    def __init__(self):

        config = config_management.load_config()
        self.YARR_URL = config['YARR_URL']
        self.STARTING_FEED = config['selected_feed']

        # Need this for PyInstaller to find the images
        if getattr(sys, 'frozen', False):
            # we are running in a bundle
            bundle_dir = sys._MEIPASS
        else:
            # we are running in a normal Python environment
            bundle_dir = os.path.dirname(os.path.abspath(__file__))

        super().__init__(parent=None, title='Yaffle')

        # Set the size based on the "dimensions" parameter in the config file if it exists
        if 'dimensions' in config:
            dimensions = config['dimensions']
            width, height = map(int, dimensions.split('x'))
            self.SetSize(width, height)
        else:
            display = wx.Display()
            screen_height = display.GetGeometry().GetHeight()
            screen_width = display.GetGeometry().GetWidth()
            self.SetSize(round(screen_width / 2), round(screen_height / 2))


        # Set the position based on the "position" parameter in the config file if it exists
        if 'position' in config:
            position = config['position']
            x, y = map(int, position.split(','))
            self.SetPosition((x, y))
        else:
            self.Centre()

        # Set the dock icon on macOS
        if sys.platform == 'darwin':
            app = NSApplication.sharedApplication()
            icon_path = os.path.join(bundle_dir, 'yaffle.png')
            icon_url = NSURL.fileURLWithPath_(icon_path)
            icon_image = NSImage.alloc().initWithContentsOfURL_(icon_url)
            app.setApplicationIconImage_(icon_image)

            # Set application menu title
            main_menu = app.mainMenu()
            app_menu_item = main_menu.itemAtIndex_(0)
            app_menu = app_menu_item.submenu()
            app_name = "Yaffle"
            app_menu_item.setTitle_(app_name)
            app_menu.setTitle_(app_name)

        self.Bind(wx.EVT_CLOSE, self.on_exit)
        feed_tree_splitter = wx.SplitterWindow(self)

        toolbar = self.CreateToolBar(style=wx.TB_HORIZONTAL | wx.NO_BORDER | wx.TB_FLAT | wx.TB_HORZ_TEXT)
        toolbar.AddTool(100, 'Show all feeds/show unread', wx.ArtProvider.GetBitmap(wx.ART_NEW_DIR, wx.ART_TOOLBAR))
        # each folder has a read/unread state, then when clicking the button it filters the items in the selected folder and uses the per-folder flag to show/hide the rest
        # wx doesn't have a way of changing tree item visibility so tree needs to be deleted and rebuilt (or switch between two trees)
        # probably loop through all items and remove feeds that are read, putting them into a different in-memory array
        # then when the button is clicked, rebuild the tree with the in-memory array, and implement OnCompareItems so we can sort the tree
        # starting status needs to be saved too and work with either selected, so all feeds still need to be fetched at startup, but filter needs to apply if it's unread only

        toolbar.AddTool(101, 'Add subscription', wx.ArtProvider.GetBitmap(wx.ART_PLUS, wx.ART_TOOLBAR))
        # toolbar.AddTool(103, 'Show starred', wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE, wx.ART_TOOLBAR))
        # toolbar.AddTool(103, 'Update feeds', wx.ArtProvider.GetBitmap(wx.ART_REDO, wx.ART_TOOLBAR))
        toolbar.Realize()

        # Add tree control and root
        self.feed_tree = wx.TreeCtrl(feed_tree_splitter, style=wx.TR_HIDE_ROOT | wx.TR_NO_LINES | wx.TR_HAS_BUTTONS | wx.TR_FULL_ROW_HIGHLIGHT)
        self.feed_tree.SetBackgroundColour(wx.Colour(249, 255, 249))
        self.feed_tree.AssignImageList(self.create_feed_image_list(bundle_dir))
        self.feed_tree.SetIndent(48)
        self.feed_tree.AddRoot('Root')

        # Create another splitter window for the list control and HTML window
        right_splitter = wx.SplitterWindow(feed_tree_splitter)

        # Set the item list as the top window of the splitter
        self.item_list = wx.ListCtrl(right_splitter, style=wx.LC_REPORT)
        self.item_list.InsertColumn(0, 'Title')

        self.web_view = wx.html2.WebView.New(right_splitter)
        self.web_view.Bind(wx.html2.EVT_WEBVIEW_NAVIGATING, self.on_webview_navigating)
        self.web_view.Bind(wx.html2.EVT_WEBVIEW_NEWWINDOW, self.on_webview_navigating) # catches links with target="_blank"

        # Set the HTML window as the bottom window of the splitter
        right_splitter.SplitHorizontally(self.item_list, self.web_view)
        right_splitter.SetSashPosition(600)  # Set the height of the list control to 300 pixels

        feed_tree_splitter.SplitVertically(self.feed_tree, right_splitter, 600)
        feed_tree_splitter.AlwaysShowScrollbars(False, True)

        self.feed_tree.Bind(wx.EVT_LEFT_DOWN, self.on_tree_item_activated)
        self.feed_tree.Bind(wx.EVT_SIZE, self.on_feed_list_resize)
        self.feed_tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_feed_tree_item_selected)
        self.feed_tree.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.on_tree_item_right_click)

        self.item_list.Bind(wx.EVT_SIZE, self.on_item_list_resize)
        self.item_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_feed_item_selected)

        # fetch the status so we know which feeds to mark as bold on startup
        self.feed_status = self.get_feed_status()
        self.initialise_feed_tree()

    def on_exit(self, event):
        config_management.save_config(self)
        self.Destroy()

    def get_feed_status(self):
        print(f"Fetching status from {self.YARR_URL}")
        response = requests.get(f"{self.YARR_URL}/api/status")
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Failed to fetch status: {response.status_code}")
            self.on_exit(wx.EVT_CLOSE)

    def on_feed_list_resize(self, event):
        # self.feed_list.SetColumnWidth(0, self.feed_list.GetSize()[0])
        event.Skip()

    def on_item_list_resize(self, event):
        self.item_list.SetColumnWidth(0, self.item_list.GetSize()[0])
        event.Skip()

    def create_feed_image_list(self, bundle_dir):
        # Load a default RSS icon and put it in the feed image list
        rss_image_path = os.path.join(bundle_dir, 'rss-32.png')
        rss_image = wx.Image(rss_image_path, wx.BITMAP_TYPE_PNG)

        rss_image = IconProcessing.load_and_pad_image(rss_image_path)

        feed_image_list = wx.ImageList(IconProcessing.ICON_SIZE[0], IconProcessing.ICON_SIZE[1])
        feed_image_list.Add(wx.Bitmap(rss_image))
        feed_image_list.Add(wx.ArtProvider.GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, IconProcessing.ICON_SIZE))
        return feed_image_list

    def process_icon(self, item):
        icon_response = requests.get(f"{self.YARR_URL}/api/feeds/{item['id']}/icon")
        if 'image' in icon_response.headers['Content-Type']:
            icon_stream = BytesIO(icon_response.content)
            image = IconProcessing.load_and_pad_image(icon_stream)
            return image
        else:
            print(f"C Failed to load image for feed {item['id']}. Unknown image data format.")
            return None

    def initialise_feed_tree(self):
        folder_response = requests.get(f"{self.YARR_URL}/api/folders")
        folder_data = folder_response.json()
        folder_dict = {0: self.feed_tree.GetRootItem()} # create a dict to hold the folder items. First item is the root

        for index, folder in enumerate(folder_data):
            # put the API-provided folder ID in the item data so we can use it to fetch feeds later
            folder_item_id = self.feed_tree.AppendItem(self.feed_tree.GetRootItem(), folder['title'], 1, -1, folder['id'])
            # we don't currently support restoring selection of a folder on exit - would need to change ItemData to denote folder or feed selected
            folder_dict[folder['id']] = folder_item_id

        feed_response = requests.get(f"{self.YARR_URL}/api/feeds")
        feed_data = feed_response.json()

        # Add each feed to the correct folder with the correct icon
        for index, item in enumerate(feed_data):
            icon_index = 0 # the default RSS icon
            if item['has_icon'] is True:
                icon = self.process_icon(item)
                if icon:
                    icon_index = self.feed_tree.GetImageList().Add(icon)

            if item['folder_id'] is None:
                item['folder_id'] = 0

            feed_item_id = self.feed_tree.AppendItem(folder_dict[item['folder_id']], str(item['title']).strip(), icon_index, -1, item['id'])
            # if this was the feed that was selected when the app was last closed, select it
            if(item['id'] == int(self.STARTING_FEED)):
                self.feed_tree.SelectItem(feed_item_id)

            # if the feed has unread items, make it bold
            if item['id'] in self.get_unread_feed_ids():
                self.feed_tree.SetItemFont(feed_item_id, self.feed_tree.GetFont().Bold())

        self.feed_tree.ExpandAll()

        if(self.feed_tree.GetSelection().IsOk() is not True):
            self.feed_tree.SelectItem(self.feed_tree.GetFirstChild(self.feed_tree.GetRootItem())[0])

        # Scroll the selected item into view and make sure it's in a reasonable place on screen
        self.feed_tree.EnsureVisible(self.feed_tree.GetSelection())
        rect = self.feed_tree.GetBoundingRect(self.feed_tree.GetSelection(), textOnly=True)
        if(rect.y > (0.8)*self.GetSize().height):
            self.feed_tree.ScrollLines(10)

    def get_unread_feed_ids(self):
        return [item['feed_id'] for item in self.feed_status['stats'] if item['unread'] > 0]

    # TreeCtrl requires double-click to expand/collapse items by default
    # This method allows expanding/collapsing items with a single click by using EVT_LEFT_DOWN
    def on_tree_item_activated(self, event):
        mouse_position=event.GetPosition()
        hit_test_result = self.feed_tree.HitTest(mouse_position)
        tree_item_id = hit_test_result[0]
        hit_test_flags = hit_test_result[1]

        if tree_item_id.IsOk() is not True:
            event.Skip()
            return

        # if you click the icon of a folder or +/-, expand/collapse it
        # otherwise select the item if it wasn't already selected
        if self.clicked_folder_or_expander(hit_test_flags):
            if self.feed_tree.ItemHasChildren(tree_item_id):
                self.feed_tree.Toggle(tree_item_id)
        else:
            if self.feed_tree.IsSelected(tree_item_id) is not True:
                self.feed_tree.SelectItem(tree_item_id)

    def clicked_folder_or_expander(self, hit_test_flags):
        # if the mouse is over the expander or the icon of a folder, return True
        return (hit_test_flags & wx.TREE_HITTEST_ONITEMICON) == wx.TREE_HITTEST_ONITEMICON or \
            (hit_test_flags & wx.TREE_HITTEST_ONITEMBUTTON) == wx.TREE_HITTEST_ONITEMBUTTON

    def populate_item_list(self, feed_id):
        response = requests.get(f"{self.YARR_URL}/api/items?feed_id={feed_id}")
        data = response.json()

        bold_font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        bold_font.SetWeight(wx.FONTWEIGHT_BOLD)

        normal_font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        normal_font.SetWeight(wx.FONTWEIGHT_NORMAL)

        for index, feed_item in enumerate(data["list"]):
            item_title = self.get_item_title(feed_item)
            item = self.item_list.InsertItem(index, item_title)
            self.item_list.SetItemData(item, feed_item['id'])

            # if the item is unread, set the font to bold
            if feed_item['status'] == "unread":
                self.item_list.SetItemFont(item, bold_font)
            else:
                # we must set a default font in order to check for unread items later
                self.item_list.SetItemFont(item, normal_font)

    def get_item_title(self, feed_item):
        if 'title' in feed_item and len(feed_item['title']) > 0:
            return str(feed_item['title'])
        elif 'date' in feed_item and len(feed_item['date']) > 0:
            return str(feed_item['date'])
        else:
            return "Untitled"

    def on_feed_tree_item_selected(self, event):
        self.item_list.DeleteAllItems()
        # if user has clicked a folder, do nothing
        if self.feed_tree.ItemHasChildren(event.GetItem()):
            return

        feed_id = self.feed_tree.GetItemData(event.GetItem())
        self.populate_item_list(feed_id)
        self.SetTitle(self.feed_tree.GetItemText(event.GetItem()) + ' - Yaffle')

    def on_tree_item_right_click(self, event):
        feed_id = self.feed_tree.GetItemData(event.GetItem())

        menu = wx.Menu()
        menu.Append(101, 'Mark all feed items as read')
        menu.Append(102, 'Rename this feed')
        self.Bind(wx.EVT_MENU, partial(self.on_context_menu_item_selected, feed_id=feed_id))

        self.PopupMenu(menu)

        menu.Destroy()

    def on_context_menu_item_selected(self, event, feed_id):
        menu_item_id = event.GetId()
        if menu_item_id == 101:
            print(f'Menu Item 1 selected for feed: {feed_id}')
            self.mark_feed_as_read(feed_id)


    def on_feed_item_selected(self, event):
        item_index = event.GetIndex()
        item_title = self.item_list.GetItemText(item_index)
        item_id = self.item_list.GetItemData(item_index)

        response = requests.get(f"{self.YARR_URL}/api/items/{item_id}")
        data = response.json()

        item_content = data['content']
        dt = datetime.fromisoformat(data['date'])
        item_date = dt.strftime("%#d %B %Y at %H:%M")

        content_start = f"""<!DOCTYPE html><html lang="en"><head>
        <link rel="stylesheet" href="{self.YARR_URL}/static/stylesheets/bootstrap.min.css">
        <link rel="stylesheet" href="{self.YARR_URL}/static/stylesheets/app.css">
        <style>.content-wrapper {{ margin: 0 auto 0 1em !important; }} h1 a {{text-decoration: none !important;}} .content-body a {{position:relative}} .content-body a[href^="http"]:hover::after {{ content: attr(href); position: absolute; left: 2em; top: -2em; min-width: 200px; border: 1px #aaaaaa solid; background-color: #ffffcc; border-radius: 10px; padding: 6px; color: #000000; font-size: 14px; z-index: 1; text-wrap: nowrap;}}</style>
        </head><body>
        <div class="content px-4 pt-3 pb-5 border-top overflow-auto" style="font-size: 1rem;"><div class="content-wrapper">
"""
        content_end = "</div></div></body>"

        content_metadata = f"""
<div class="text-muted"><div>{self.feed_tree.GetItemText(self.feed_tree.GetSelection())}</div> <time>{item_date}</time></div>
"""

        content = f"{content_start}<h1><a href=\"{data['link']}\">{item_title}</a></h1>{content_metadata}<hr><div class='content-body'>{item_content}</div>{content_end}"

        self.web_view.SetPage(content, "")
        self.mark_item_as_read(item_id, item_index)

    def on_webview_navigating(self, event):
        if(event.GetNavigationAction() == wx.html2.WEBVIEW_NAV_ACTION_USER and event.GetURL() != "about:blank" and not event.GetURL().startswith("data:text/html")):
            webbrowser.open(event.GetURL())

    def mark_feed_as_read(self, feed_id):
        requests.put(f"{self.YARR_URL}/api/items?feed_id={feed_id}&status=unread") # mark all items as read
        # TODO: mark the feed as read in the tree - use the code from the method below refactored into a separate method

    def mark_item_as_read(self, item_id, item_index):
        requests.put(f"{self.YARR_URL}/api/items/{item_id}", json={"status": "read"})

        # set the item font to normal
        normal_font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        normal_font.SetWeight(wx.FONTWEIGHT_NORMAL)
        self.item_list.SetItemFont(item_index, normal_font)

        # if no more unread items in the list, mark the feed as read
        if not any([self.item_list.GetItemFont(index).GetWeight() == wx.FONTWEIGHT_BOLD \
                for index in range(self.item_list.GetItemCount())]):
            normal_font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            normal_font.SetWeight(wx.FONTWEIGHT_NORMAL)
            self.feed_tree.SetItemFont(self.feed_tree.GetSelection(), normal_font)

    def mark_item_as_unread(self, item_id, item_index):
        requests.put(f"{self.YARR_URL}/api/items/{item_id}", json={"status": "unread"})
        normal_font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        normal_font.SetWeight(wx.FONTWEIGHT_BOLD)
        self.item_list.SetItemFont(item_index, normal_font)

if __name__ == '__main__':
    app = wx.App()
    frame = YaffleFrame()
    frame.Show()
    app.MainLoop()
