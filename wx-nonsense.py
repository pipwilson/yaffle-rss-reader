import wx
import requests
import ctypes
import json
import tempfile
import os
from io import BytesIO
from PIL import Image

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(True)
except:
    pass

class MyFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title='Yaffle')
        self.SetSize(3200, 1200)
        splitter = wx.SplitterWindow(self)
        self.feed_list = wx.ListCtrl(splitter, style=wx.LC_REPORT)
        self.feed_list.InsertColumn(0, 'Title', 0, 400)

        self.feed_image_list = wx.ImageList(48, 48)
        self.feed_list.AssignImageList(self.feed_image_list, wx.IMAGE_LIST_SMALL)

        # Load a default RSS icon and put it in the feed image list
        image = wx.Image('rss.png', wx.BITMAP_TYPE_PNG).Scale(48, 48, wx.IMAGE_QUALITY_HIGH)
        bitmap = wx.Bitmap(image)
        self.feed_image_list.Add(bitmap)

        self.item_list = wx.ListCtrl(splitter, style=wx.LC_REPORT)
        self.item_list.InsertColumn(0, 'Title')

        splitter.SplitVertically(self.feed_list, self.item_list, 400)
        self.populate_feed_list()
        self.Show()

        self.feed_list.Bind(wx.EVT_SIZE, self.on_feed_list_resize)
        self.item_list.Bind(wx.EVT_SIZE, self.on_item_list_resize)
        self.feed_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_feed_selected)  # Bind event

    def on_feed_list_resize(self, event):
        self.feed_list.SetColumnWidth(0, self.feed_list.GetSize()[0])
        event.Skip()

    def on_item_list_resize(self, event):
        self.item_list.SetColumnWidth(0, self.item_list.GetSize()[0])
        event.Skip()

    def process_icon(self, item, index):
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

            wx_image = wx_image.Scale(48, 48, wx.IMAGE_QUALITY_HIGH)
            bitmap = wx.Bitmap(wx_image)
            img_index = self.feed_image_list.Add(bitmap)
            self.feed_list.SetItemImage(index, img_index)
        else:
            print(f"C Failed to load image for feed {item['id']}. Unknown image data format.")


    def populate_feed_list(self):
        response = requests.get("http://127.0.0.1:7070/api/feeds")
        data = response.json()
        # with open('subscriptions.json') as f:
        #     data = json.load(f)
        for index, item in enumerate(data):
            self.feed_list.InsertItem(index, str(item['title']).strip())
            self.feed_list.SetItemData(index, item['id'])
            if item['has_icon'] is True:
                self.process_icon(item, index)
            else:
                self.feed_list.SetItemImage(index, 0) # the default RSS icon

    def populate_item_list(self, feed_id):
        response = requests.get(f"http://127.0.0.1:7070/api/items?feed_id={feed_id}")
        data = response.json()
        for index, item in enumerate(data["list"]):
            self.item_list.InsertItem(index, str(item['title']))

    def on_feed_selected(self, event):
        self.item_list.DeleteAllItems()
        feed_id = self.feed_list.GetItemData(event.GetIndex())
        self.populate_item_list(feed_id)

if __name__ == '__main__':
    app = wx.App()
    frame = MyFrame()
    app.MainLoop()