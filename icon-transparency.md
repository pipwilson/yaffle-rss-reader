About transparency

The ICO format has an inherent 1 bit transparency mask (0 = opaque, 1 = transparent), called the AND bitmap.

    When reading or saving an RGB mode image in Photoshop 6.0 or later, layer transparency is used for the mask
    If the image is Indexed mode, and uses a "transparent index", this will be used to set the icon mask
    In other cases, the ICO mask is treated as an alpha channel (black = 0 = opaque, white = 255 = transparent)
    In PNG (Vista) format icons, the alpha channel is simply stored as part of the PNG. There is no separate mask.