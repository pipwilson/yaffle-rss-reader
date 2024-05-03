import wx
from PIL import ImageOps

class IconProcessing:

    ICON_SIZE = (58, 58) # account for 10px transparent padding

    @staticmethod
    def scale_image(image):
        image = wx.Image(image)
        image = image.Scale(IconProcessing.ICON_SIZE[0], IconProcessing.ICON_SIZE[1], wx.IMAGE_QUALITY_HIGH)
        return wx.Bitmap(image)

    @staticmethod
    def add_padding_to_image(pil_image):
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

            return wx.Bitmap(IconProcessing.scale_image(wx_image))
        except Exception as e:
            print("Failed to parse image.")
            print(e)
            return None
