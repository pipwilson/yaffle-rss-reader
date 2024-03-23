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
        self.tree = wx.TreeCtrl(self, style=wx.TR_HIDE_ROOT | wx.TR_NO_LINES | wx.TR_HAS_BUTTONS | wx.TR_FULL_ROW_HIGHLIGHT)

        isz = (48,48)
        il = wx.ImageList(isz[0], isz[1])
        fldridx     = il.Add(wx.ArtProvider.GetBitmap(wx.ART_FOLDER,      wx.ART_OTHER, isz))
        fileidx     = il.Add(wx.ArtProvider.GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, isz))
        self.tree.SetImageList(il)
        self.il = il

        self.root = self.tree.AddRoot('Feeds')
        self.tree.SetItemImage(self.root, fldridx, wx.TreeItemIcon_Normal)

        # Add some folders (sub-items)
        folder1 = self.tree.AppendItem(self.root, 'Feeds')
        self.tree.SetItemImage(folder1, fldridx, wx.TreeItemIcon_Normal)

        folder2 = self.tree.AppendItem(self.root, 'Podcasts')
        self.tree.SetItemImage(folder2, fldridx, wx.TreeItemIcon_Normal)

        folder3 = self.tree.AppendItem(folder1, 'More feeds')
        self.tree.SetItemImage(folder3, fldridx, wx.TreeItemIcon_Normal)

        # Add some feeds (sub-sub-items)
        file1 = self.tree.AppendItem(folder1, 'Feed 1.1')
        self.tree.SetItemImage(file1, fileidx, wx.TreeItemIcon_Normal)
        file2 = self.tree.AppendItem(folder1, 'Feed 1.2')
        self.tree.SetItemImage(file2, fileidx, wx.TreeItemIcon_Normal)
        file3 = self.tree.AppendItem(folder1, 'Feed 2.1')
        self.tree.SetItemImage(file3, fileidx, wx.TreeItemIcon_Normal)
        file4 = self.tree.AppendItem(folder3, 'Feed 1.1.1')
        self.tree.SetItemImage(file4, fileidx, wx.TreeItemIcon_Normal)

        self.tree.Expand(folder1)
        self.tree.Expand(folder2)
        self.tree.Expand(folder3)

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

        # if you click the icon of a folder or +/-, expand/collapse it
        # otherwise select the item if it wasn't already selected
        if(self.clicked_folder_or_expander(hit_test_flags)):
            if(self.tree.ItemHasChildren(tree_item_id)):
                self.tree.Toggle(tree_item_id)
        else:
            if(self.tree.IsSelected(tree_item_id) is not True):
                self.tree.SelectItem(tree_item_id)


    def clicked_folder_or_expander(self, hit_test_flags):
        # if the mouse is over the expander or the icon of a folder, return True
        # if the mouse is over the text of a folder, return False
        return (hit_test_flags & wx.TREE_HITTEST_ONITEMICON) == wx.TREE_HITTEST_ONITEMICON or (hit_test_flags & wx.TREE_HITTEST_ONITEMBUTTON) == wx.TREE_HITTEST_ONITEMBUTTON

    def on_item_expanded(self, event):
        item = event.GetItem()
        # self.tree.SetItemImage(item, self.open_folder)

    def on_item_collapsed(self, event):
        item = event.GetItem()
        # self.tree.SetItemImage(item, self.closed_folder)

    def on_feed_selected(self, event):
        item = event.GetItem()
        print('Selected feed:', self.tree.GetItemText(item))


app = wx.App()
frame = MyFrame(None)
frame.Show(True)
app.MainLoop()