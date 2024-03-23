import wx
import requests
import ctypes
import json
import os
import sys
from io import BytesIO
from PIL import Image

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(True)
except:
    pass

class MyFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title='Yaffle')
        self.SetSize(2000, 1200)
        splitter = wx.SplitterWindow(self)

        # Add tree control and root
        self.feed_tree = wx.TreeCtrl(splitter, style=wx.TR_HIDE_ROOT | wx.TR_NO_LINES | wx.TR_HAS_BUTTONS | wx.TR_FULL_ROW_HIGHLIGHT)
        self.feed_tree.AssignImageList(self.create_feed_image_list())

        tree_root = self.feed_tree.AddRoot('Root')
        feeds_root = self.feed_tree.AppendItem(tree_root, 'Feeds')
        self.feed_tree.SetItemImage(feeds_root, 1)

        self.item_list = wx.ListCtrl(splitter, style=wx.LC_SMALL_ICON)
        self.item_list.InsertColumn(0, 'Title')

        splitter.SplitVertically(self.feed_tree, self.item_list, 600)
        splitter.AlwaysShowScrollbars(False, True)
        
        # self.feed_list.Bind(wx.EVT_SIZE, self.on_feed_list_resize)
        # self.item_list.Bind(wx.EVT_SIZE, self.on_item_list_resize)
        # self.feed_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_feed_selected)

        self.initialise_feed_tree()

    def create_feed_image_list(self):
        # Need this for PyInstaller to find the images
        if getattr(sys, 'frozen', False):
            # we are running in a bundle
            bundle_dir = sys._MEIPASS
        else:
            # we are running in a normal Python environment
            bundle_dir = os.path.dirname(os.path.abspath(__file__))

        icon_size = (32, 32)

        # Load a default RSS icon and put it in the feed image list
        rss_image_path = os.path.join(bundle_dir, 'rss-32.png')
        rss_image = wx.Image(rss_image_path, wx.BITMAP_TYPE_PNG).Scale(icon_size[0], icon_size[1], wx.IMAGE_QUALITY_HIGH)
        
        feed_image_list = wx.ImageList(icon_size[0], icon_size[1])
        feed_image_list.Add(wx.Bitmap(rss_image))
        feed_image_list.Add(wx.ArtProvider.GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, feed_image_list.GetSize()))
        return feed_image_list

    def on_feed_list_resize(self, event):
        self.feed_list.SetColumnWidth(0, self.feed_list.GetSize()[0])
        event.Skip()

    def on_item_list_resize(self, event):
        self.item_list.SetColumnWidth(0, self.item_list.GetSize()[0])
        event.Skip()

    def process_icon(self, item, icon_size):
        icon_response = requests.get(f"http://127.0.0.1:7070/api/feeds/{item['id']}/icon")
        if 'image' in icon_response.headers['Content-Type']:
            icon_stream = BytesIO(icon_response.content)

            # we have to use Pillow here because trying to open an icon with transparency in wx.Image
            # throws a user-facing error messagebox in wxPython
            pil_image = Image.open(icon_stream)
            pil_image.load()

            # if an icon has transparency, extract it and apply it to a white background
            if pil_image.mode == 'RGBA':
                background = Image.new("RGB", pil_image.size, (255, 255, 255))
                background.paste(pil_image, mask=pil_image.split()[3]) # 3 is the alpha channel
            else:
                background = pil_image.convert('RGB')

            wx_image = wx.Image(pil_image.size[0], pil_image.size[1])
            wx_image.SetData(background.tobytes())

            wx_image = wx_image.Scale(icon_size[0], icon_size[1], wx.IMAGE_QUALITY_HIGH)
            return wx.Bitmap(wx_image)
        else:
            print(f"C Failed to load image for feed {item['id']}. Unknown image data format.")

    def initialise_feed_tree(self):
        response = requests.get("http://127.0.0.1:7070/api/feeds")
        response = requests.get("http://127.0.0.1:7070/api/feeds")
        data = response.json()
        # with open('subscriptions.json') as f:
        #     data = json.load(f)

        icon_size = self.feed_tree.GetImageList().GetSize(0)

        for index, item in enumerate(data):
            subscription = self.feed_tree.AppendItem(self.feed_tree.GetFirstChild(self.feed_tree.GetRootItem())[0], str(item['title']).strip())
            
            self.feed_tree.SetItemData(subscription, item['id'])
            if item['has_icon'] is True:
                icon = self.process_icon(item, icon_size)
                icon_index = self.feed_tree.GetImageList().Add(icon)
                self.feed_tree.SetItemImage(subscription, icon_index)
            else:
                self.feed_tree.SetItemImage(subscription, 0) # the default RSS icon
        
        self.feed_tree.SetIndent(48)
        self.feed_tree.ExpandAll()
        
        first_folder = self.feed_tree.GetFirstChild(self.feed_tree.GetRootItem())[0]
        first_feed = self.feed_tree.GetFirstChild(first_folder)[0]
        self.feed_tree.SelectItem(first_feed)
        
        # absolute hack - this is the only way to scroll the first item into view. EnsureVisible doesn't work
        # and nor does calling EnsureVisible on the parent
        self.feed_tree.ScrollLines(-2) 
           
    # TreeCtrl requires double-click to expand/collapse items by default
    # This method allows expanding/collapsing items with a single click by using the EVT_LEFT_DOWN event
    def on_item_activated(self, event):
        mouse_position=event.GetPosition()
        hit_test_result = self.feed_tree.HitTest(mouse_position)
        tree_item_id = hit_test_result[0]
        hit_test_flags = hit_test_result[1]

        if(tree_item_id.IsOk() is not True):
            event.Skip()
            return

        # if you click the icon of a folder or +/-, expand/collapse it
        # otherwise select the item if it wasn't already selected
        if(self.clicked_folder_or_expander(hit_test_flags)):
            if(self.feed_tree.ItemHasChildren(tree_item_id)):
                self.feed_tree.Toggle(tree_item_id)
        else:
            if(self.feed_tree.IsSelected(tree_item_id) is not True):
                self.feed_tree.SelectItem(tree_item_id)


    def clicked_folder_or_expander(self, hit_test_flags):
        # if the mouse is over the expander or the icon of a folder, return True
        # if the mouse is over the text of a folder, return False
        return (hit_test_flags & wx.TREE_HITTEST_ONITEMICON) == wx.TREE_HITTEST_ONITEMICON or (hit_test_flags & wx.TREE_HITTEST_ONITEMBUTTON) == wx.TREE_HITTEST_ONITEMBUTTON


    def populate_item_list(self, feed_id):
        response = requests.get(f"http://127.0.0.1:7070/api/items?feed_id={feed_id}")
        data = response.json()
        for index, item in enumerate(data["list"]):
            self.item_list.InsertItem(index, str(item['title']))

    def on_feed_selected(self, event):
        self.item_list.DeleteAllItems()
        feed_id = self.feed_list.GetItemData(event.GetIndex())
        self.populate_item_list(feed_id)
        feed_name = self.feed_list.GetItemText(event.GetIndex())
        self.SetTitle(feed_name + ' - Yaffle')

if __name__ == '__main__':
    app = wx.App()
    frame = MyFrame()
    frame.Show()
    app.MainLoop()