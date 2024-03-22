import wx
import os
import win32api
import ctypes

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(True)
except:
    pass

class MyFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, "TreeCtrl Demo")

        # Create a TreeCtrl with expand/collapse buttons
        self.tree = wx.TreeCtrl(self, style=wx.TR_HIDE_ROOT | wx.TR_HAS_BUTTONS | wx.TR_FULL_ROW_HIGHLIGHT)
        root = self.tree.AddRoot('Feeds')

        # Add some folders (sub-items)
        folder1 = self.tree.AppendItem(root, 'Folder 1')
        folder2 = self.tree.AppendItem(root, 'Folder 2')

        # Add some feeds (sub-sub-items)
        self.tree.AppendItem(folder1, 'Feed 1.1')
        self.tree.AppendItem(folder1, 'Feed 1.2')
        self.tree.AppendItem(folder2, 'Feed 2.1')

        imageList = wx.ImageList(16, 16)
        # self.closed_folder = imageList.Add(wx.ArtProvider.GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, (16,16)))
        #shell32 = win32api.GetModuleFileName(win32api.GetModuleHandle('shell32.dll'))
        #self.closed_folder = imageList.Add(wx.Icon(shell32 + ';43', wx.BITMAP_TYPE_ICO, desiredWidth=16, desiredHeight=16))
       
        chevron_right_path = os.path.join('.', 'chevron-right.png')
        self.closed_folder = imageList.Add(wx.Bitmap(wx.Image(chevron_right_path, wx.BITMAP_TYPE_PNG)))

        chevron_down_path = os.path.join('.', 'chevron-down.png')
        self.open_folder = imageList.Add(wx.Bitmap(wx.Image(chevron_down_path, wx.BITMAP_TYPE_PNG)))

        self.normal_file = imageList.Add(wx.ArtProvider.GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, (16,16)))
        
        self.tree.AssignImageList(imageList)

        self.tree.SetItemImage(root, self.closed_folder)
        self.tree.SetItemImage(folder1, self.closed_folder)
        self.tree.SetItemImage(folder2, self.closed_folder)
        self.tree.SetItemImage(self.tree.AppendItem(folder1, 'Feed 1.1'), self.normal_file)

        self.tree.Expand(folder1)
        self.tree.Expand(folder2)

        self.tree.Bind(wx.EVT_LEFT_DOWN, self.on_item_activated)

        self.tree.Bind(wx.EVT_TREE_ITEM_EXPANDED, self.on_item_expanded)
        self.tree.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.on_item_collapsed)

        # Create a sizer and add the tree to it
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.tree, 1, wx.EXPAND)

        # Set the sizer as the frame's sizer
        self.SetSizer(sizer)

    # TreeCtrl requires double-click to expand/collapse items by default
    # This method allows expanding/collapsing items with a single click by using the EVT_LEFT_DOWN event
    def on_item_activated(self, event):
        mouse_position=event.GetPosition()
        hit_test_result = self.tree.HitTest(mouse_position)
        tree_item_id = hit_test_result[0]
        hit_test_flags = hit_test_result[1]

        if(tree_item_id.IsOk() is not True):
            event.Skip()
            return

        # if you click the icon of a folder, expand/collapse it
        # otherwise select the item if it wasn't already selected
        if((hit_test_flags & wx.TREE_HITTEST_ONITEMICON) == wx.TREE_HITTEST_ONITEMICON):
            if(self.tree.ItemHasChildren(tree_item_id)):
                self.tree.Toggle(tree_item_id)
        else:
            if(self.tree.IsSelected(tree_item_id) is not True):
                self.tree.SelectItem(tree_item_id)


    def on_item_expanded(self, event):
        item = event.GetItem()
        self.tree.SetItemImage(item, self.open_folder)

    def on_item_collapsed(self, event):
        item = event.GetItem()
        self.tree.SetItemImage(item, self.closed_folder)

    def on_feed_selected(self, event):
        item = event.GetItem()
        print('Selected feed:', self.tree.GetItemText(item))


app = wx.App()
frame = MyFrame(None)
frame.Show(True)
app.MainLoop()