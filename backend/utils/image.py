"""Image URL helpers — CDN-specific quality upgrades and responsive sizing."""

import re


def upgrade_image_quality(image_url: str, size: str = "500x500") -> str:
    """
    Swap the size token in a CDN image URL to a higher-quality version.

    Supports JioSaavn (saavncdn.com) and YouTube (ytimg.com) URLs.
    Returns the original URL unchanged if no size token is found.
    """
    if not image_url or not isinstance(image_url, str):
        return image_url

    if "saavncdn.com" in image_url or "jiosaavn.com" in image_url:
        image_url = re.sub(r"-(50x50|150x150|250x250)\.", f"-{size}.", image_url)
        if size not in image_url:
            image_url = re.sub(
                r"\.(jpg|jpeg|png|webp)$", f"-{size}.\\1", image_url, flags=re.IGNORECASE
            )
    elif "ytimg.com" in image_url or "youtube.com" in image_url:
        for low_q in ("default.jpg", "mqdefault.jpg", "hqdefault.jpg"):
            image_url = image_url.replace(low_q, "maxresdefault.jpg")

    return image_url


def get_responsive_image_url(image_url: str, size: str = "medium") -> str:
    """
    Return a CDN URL resized to *size* ("small" | "medium" | "large").

    Size map:
        small  → 150×150
        medium → 250×250
        large  → 500×500
    """
    if not image_url or not isinstance(image_url, str):
        return image_url

    size_map = {"small": "150x150", "medium": "250x250", "large": "500x500"}
    target = size_map.get(size, "250x250")
    w, h = target.split("x")

    # JioSaavn — -150x150.jpg
    if "saavncdn.com" in image_url or "jiosaavn.com" in image_url:
        new = re.sub(r"-(\d+x\d+)\.(jpg|jpeg|png|webp)", f"-{target}.\\2", image_url, flags=re.IGNORECASE)
        if new != image_url:
            return new
        return re.sub(r"-(\d+x\d+)", f"-{target}", image_url)

    # Google / YouTube Music — w120-h120-l90-rj
    if "googleusercontent.com" in image_url or "ggpht.com" in image_url:
        return re.sub(r"w\d+-h\d+", f"w{w}-h{h}", image_url)

    # SoundCloud — t500x500.jpg / -large.jpg
    if "sndcdn.com" in image_url or "soundcloud.com" in image_url:
        if size == "small":
            target = "250x250"
        new = re.sub(r"t(\d+x\d+)\.(jpg|jpeg|png|webp)", f"t{target}.\\2", image_url, flags=re.IGNORECASE)
        if new != image_url:
            return new
        return image_url.replace("-large.", f"-t{target}.")

    # YouTube thumbnails — strip signed query params, swap filename
    if "ytimg.com" in image_url or "youtube.com" in image_url:
        base = image_url.split("?")[0]
        if size == "large":
            base = re.sub(r"/(default|mqdefault|sddefault|hqdefault)\.jpg$", "/maxresdefault.jpg", base)
        elif size == "medium":
            base = re.sub(r"/(default|mqdefault|sddefault|maxresdefault)\.jpg$", "/hqdefault.jpg", base)
        else:
            base = re.sub(r"/(mqdefault|sddefault|hqdefault|maxresdefault)\.jpg$", "/mqdefault.jpg", base)
        return base

    return image_url
