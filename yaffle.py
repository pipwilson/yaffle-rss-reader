import ctypes
import os
import sys
from io import BytesIO
from datetime import datetime

import wx
import wx.html2
import requests
from PIL import Image, ImageOps

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(True)
except:
    pass

class MyFrame(wx.Frame):

    YARR_URL = "http://127.0.0.1:7070"
    icon_size = (58, 58) # account for 10px transparent padding

    def __init__(self):

        # Need this for PyInstaller to find the images
        if getattr(sys, 'frozen', False):
            # we are running in a bundle
            bundle_dir = sys._MEIPASS
        else:
            # we are running in a normal Python environment
            bundle_dir = os.path.dirname(os.path.abspath(__file__))

        super().__init__(parent=None, title='Yaffle')
        self.SetSize(2000, 1200)
        self.SetPosition(wx.Point(500, 500))
        self.SetIcon(wx.Icon(os.path.join(bundle_dir, 'yaffle.png'), wx.BITMAP_TYPE_PNG))
        feed_tree_splitter = wx.SplitterWindow(self)

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

        # Set the HTML window as the bottom window of the splitter
        right_splitter.SplitHorizontally(self.item_list, self.web_view)
        right_splitter.SetSashPosition(600)  # Set the height of the list control to 300 pixels

        feed_tree_splitter.SplitVertically(self.feed_tree, right_splitter, 600)
        feed_tree_splitter.AlwaysShowScrollbars(False, True)

        self.feed_tree.Bind(wx.EVT_LEFT_DOWN, self.on_tree_item_activated)
        self.feed_tree.Bind(wx.EVT_SIZE, self.on_feed_list_resize)
        self.feed_tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_feed_tree_item_selected)

        self.item_list.Bind(wx.EVT_SIZE, self.on_item_list_resize)
        self.item_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_feed_item_selected)

        # fetch the status so we know which feeds to mark as bold on startup
        self.feed_status = self.get_feed_status()
        self.initialise_feed_tree()

    def get_feed_status(self):
        response = requests.get(f"{self.YARR_URL}/api/status")
        data = response.json()
        return data

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

        pil_image = Image.open(rss_image_path)
        pil_image.load()

        # Create a BytesIO object from the bytes
        rss_image = self.add_padding_to_image(pil_image)

        feed_image_list = wx.ImageList(self.icon_size[0], self.icon_size[1])
        feed_image_list.Add(wx.Bitmap(rss_image))
        feed_image_list.Add(wx.ArtProvider.GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, self.icon_size))
        return feed_image_list

    def scale_image(self, image):
        image = wx.Image(image)
        image = image.Scale(self.icon_size[0], self.icon_size[1], wx.IMAGE_QUALITY_HIGH)
        return wx.Bitmap(image)

    def add_padding_to_image(self, pil_image):
        try:
            # we have to use Pillow here because trying to open an icon with transparency in wx.Image
            # throws a user-facing error messagebox in wxPython
            pil_image.load()

            if pil_image.mode != 'RGBA':
                pil_image = pil_image.convert('RGBA')

            # Add a transparent margin to the image
            margin = 10  # The size of the margin
            pil_image_with_margin = ImageOps.expand(pil_image, border=margin, fill=(0, 0, 0, 0))

            wx_image = wx.Image(pil_image_with_margin.size[0], pil_image_with_margin.size[1])
            wx_image.SetData(pil_image_with_margin.convert('RGB').tobytes())
            wx_image.SetAlpha(pil_image_with_margin.convert('RGBA').tobytes()[3::4])

            return wx.Bitmap(self.scale_image(wx_image))
        except Exception as e:
            print(f"C Failed to parse image.")
            print(e)
            return None

    def process_icon(self, item, icon_size):
        icon_response = requests.get(f"{self.YARR_URL}/api/feeds/{item['id']}/icon")
        if 'image' in icon_response.headers['Content-Type']:
            try:
                icon_stream = BytesIO(icon_response.content)
                pil_image = Image.open(icon_stream)
                pil_image.load()
            except Exception as e:
                print(f"C Failed to parse image.")
                print(e)
                return None

            return self.add_padding_to_image(pil_image)
        else:
            print(f"C Failed to load image for feed {item['id']}. Unknown image data format.")
            return None

    def initialise_feed_tree(self):
        folder_response = requests.get(f"{self.YARR_URL}/api/folders")
        folder_data = folder_response.json()
        folder_array = [self.feed_tree.GetRootItem()] # create an array to hold the folder items. First item is the root
        feed_array = []

        for index, folder in enumerate(folder_data):
            folder_item_id = self.feed_tree.AppendItem(self.feed_tree.GetRootItem(), folder['title'], 1, -1, folder['id'])
            folder_array.append(folder_item_id)

        feed_response = requests.get(f"{self.YARR_URL}/api/feeds")
        feed_data = feed_response.json()

        # Add each feed to the correct folder with the correct icon
        for index, item in enumerate(feed_data):
            icon_index = 0 # the default RSS icon
            if item['has_icon'] is True:
                icon = self.process_icon(item, self.feed_tree.GetImageList().GetSize(0))
                if icon:
                    icon_index = self.feed_tree.GetImageList().Add(icon)

            if item['folder_id'] is None:
                item['folder_id'] = folder_array[0]

            feed_item_id = self.feed_tree.AppendItem(folder_array[item['folder_id']], str(item['title']).strip(), icon_index, -1, item['id'])
            feed_array.append(feed_item_id)

            # if the feed has unread items, make it bold
            if item['id'] in self.get_unread_feed_ids():
                self.feed_tree.SetItemFont(feed_item_id, self.feed_tree.GetFont().Bold())

        self.feed_tree.ExpandAll()

        # self.feed_tree.SelectItem(feed_array[0])
        # self.feed_tree.SelectItem(folder_array[1])

        # absolute hack - this is the only way to scroll the first item into view.
        # EnsureVisible doesn't work and nor does calling EnsureVisible on the parent
        # self.feed_tree.EnsureVisible(folder_array[1])
        self.feed_tree.ScrollLines(-10)

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
            item = self.item_list.InsertItem(index, str(feed_item['title']))
            self.item_list.SetItemData(item, feed_item['id'])

            # if the item is unread, set the font to bold
            if feed_item['status'] == "unread":
                self.item_list.SetItemFont(item, bold_font)
            else:
                # we must set a default font in order to check for unread items later
                self.item_list.SetItemFont(item, normal_font)

    def on_feed_tree_item_selected(self, event):
        self.item_list.DeleteAllItems()
        # if user has clicked a folder, do nothing
        if self.feed_tree.ItemHasChildren(event.GetItem()):
            return

        feed_id = self.feed_tree.GetItemData(event.GetItem())
        self.populate_item_list(feed_id)
        self.SetTitle(self.feed_tree.GetItemText(event.GetItem()) + ' - Yaffle')

    def on_feed_item_selected(self, event):
        item_index = event.GetIndex()
        item_title = self.item_list.GetItemText(item_index)
        item_id = self.item_list.GetItemData(item_index)

        response = requests.get(f"{self.YARR_URL}/api/items/{item_id}")
        data = response.json()

        item_content = data['content']
        dt = datetime.strptime(data['date'], "%Y-%m-%dT%H:%M:%SZ")
        item_date = dt.strftime("%#d %B %Y at %H:%M")

        content_start = f"""
        <link rel="stylesheet" href="{self.YARR_URL}/static/stylesheets/bootstrap.min.css">
        <link rel="stylesheet" href="{self.YARR_URL}/static/stylesheets/app.css">
        <style>.content-wrapper {{ margin: 0 auto 0 1em !important; }} h1 a {{text-decoration: none !important;}}</style>
        <div class="content px-4 pt-3 pb-5 border-top overflow-auto" style="font-size: 1rem;"><div class="content-wrapper">
"""
        content_end = "</div></div>"

        content_metadata = f"""
<div class="text-muted"><div>{self.feed_tree.GetItemText(self.feed_tree.GetSelection())}</div> <time>{item_date}</time></div>
"""

        content = f"{content_start}<h1><a href=\"{data['link']}\">{item_title}</a></h1>{content_metadata}<hr>{item_content}{content_end}"

        self.web_view.SetPage(content, "")
        self.mark_item_as_read(item_id, item_index)

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
    frame = MyFrame()
    frame.Show()
    app.MainLoop()