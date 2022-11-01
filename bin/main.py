#!/usr/bin/python3
# -*- coding: utf-8 -*-

from configparser import ConfigParser
import urllib.request
import urllib.error
from subprocess import check_output
from gi.repository import Notify
from gi.repository import Gtk
from gi.repository import Gio
import gi
import xml.etree.ElementTree as ET
import locale
import re
import sys
import pathlib
import time

gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')

BING_MARKETS = [u'ar-XA',
                u'bg-BG',
                u'cs-CZ',
                u'da-DK',
                u'de-AT',
                u'de-CH',
                u'de-DE',
                u'el-GR',
                u'en-AU',
                u'en-CA',
                u'en-GB',
                u'en-ID',
                u'en-IE',
                u'en-IN',
                u'en-MY',
                u'en-NZ',
                u'en-PH',
                u'en-SG',
                u'en-US',
                u'en-XA',
                u'en-ZA',
                u'es-AR',
                u'es-CL',
                u'es-ES',
                u'es-MX',
                u'es-US',
                u'es-XL',
                u'et-EE',
                u'fi-FI',
                u'fr-BE',
                u'fr-CA',
                u'fr-CH',
                u'fr-FR',
                u'he-IL',
                u'hr-HR',
                u'hu-HU',
                u'it-IT',
                u'ja-JP',
                u'ko-KR',
                u'lt-LT',
                u'lv-LV',
                u'nb-NO',
                u'nl-BE',
                u'nl-NL',
                u'pl-PL',
                u'pt-BR',
                u'pt-PT',
                u'ro-RO',
                u'ru-RU',
                u'sk-SK',
                u'sl-SL',
                u'sv-SE',
                u'th-TH',
                u'tr-TR',
                u'uk-UA',
                u'zh-CN',
                u'zh-HK',
                u'zh-TW']

config_file_skeleton = """[market]
# If you want to override the current Bing market detection,
# set your preferred market here. For a list of markets, see
# https://msdn.microsoft.com/en-us/library/dd251064.aspx
area =
[directory]
# Download directory path. By default images are saved to
# /home/[user]/[Pictures]/BingWallpapers/
dir_path =
# Limit the size of the downloaded image directory
# Size should be specified in bytes. The minimum
# limit is the size of 1 image (whatever size that image is)
# Set to negative value for unlimit. Default value is 100MiB
dir_max_size =
"""


def get_file_uri(filename):
    return f'file://{filename}'


def set_gsetting(schema, key, value):
    gsettings = Gio.Settings.new(schema)
    gsettings.set_string(key, value)
    gsettings.apply()


def change_background(filename, desktop_environment):
    set_gsetting(f'org.{desktop_environment}.desktop.background', 'picture-uri',
                 get_file_uri(filename))


def get_current_background_uri(desktop_environment):
    gsettings = Gio.Settings.new(f'org.{desktop_environment}.desktop.background')
    path = gsettings.get_string('picture-uri')
    return pathlib.Path(path[7:])


def change_screensaver(filename, desktop_environment):
    set_gsetting(f'org.{desktop_environment}.desktop.screensaver', 'picture-uri',
                 get_file_uri(filename))


def get_config_file():
    """
    Get the path to the program's config file.

    :return: Path to the program's config file.
    """
    config_dir = pathlib.Path.home() / '.config/bing-desktop-wallpaper-changer'
    init_dir(config_dir)
    config_path = config_dir / 'config.ini'
    if not config_path.is_file():
        with open(config_path, 'w') as config_file:
            config_file.write(config_file_skeleton)
    return config_path


def get_market():
    """
    Get the desired Bing Market.

    In order of preference, this program will use:
    * Config value market.area from desktop_wallpaper_changer.ini
    * Default locale, in case that's a valid Bing market
    * Fallback value is 'en-US'.

    :return: Bing Market
    :rtype: str
    """
    config = ConfigParser()
    config.read(get_config_file())
    market_area_override = config.get('market', 'area')
    if market_area_override:
        return market_area_override

    default_locale = locale.getdefaultlocale()[0]
    if default_locale in BING_MARKETS:
        return default_locale

    return 'en-US'


def get_download_path():
    # By default images are saved to '/home/[user]/[Pictures]/BingWallpapers/'
    default_path = check_output("xdg-user-dir PICTURES", shell=True).strip().decode("utf-8") + "/BingWallpapers"

    try:
        config = ConfigParser()
        config.read(get_config_file())
        path = config.get('directory', 'dir_path')

        return pathlib.Path(path or default_path)
    except Exception:
        return pathlib.Path(default_path)


def get_directory_limit():
    """
    Get the directory sized limit
    """
    config = ConfigParser()
    config.read(get_config_file())
    try:
        size = config.getint('directory', 'dir_max_size')
        return size
    except Exception:
        return 100 * 1024 * 1024


def get_bing_xml():
    """
    Get BingXML file which contains the URL of the Bing Photo of the day.

    :return: URL with the Bing Photo of the day.
    """
    # idx = Number days previous the present day.
    # 0 means today, 1 means yesterday
    # n = Number of images previous the day given by idx
    # mkt = Bing Market Area, see get_valid_bing_markets.
    market = get_market()
    return f"https://www.bing.com/HPImageArchive.aspx?format=xml&idx=0&n=1&mkt={market}"


def get_maximum_screen_resolution():
    window = Gtk.Window()
    screen = window.get_screen()
    nmons = screen.get_n_monitors()
    maxw = 0
    maxh = 0
    if nmons == 1:
        maxw = screen.get_width()
        maxh = screen.get_height()
    else:
        for m in range(nmons):
            mg = screen.get_monitor_geometry(m)
            if mg.width > maxw or mg.height > maxw:
                maxw = mg.width
                maxh = mg.height

    return maxw, maxh


def get_screen_resolution_str():
    """
    Get a regexp like string with your current screen resolution.

    :return: String with your current screen resolution.
    """
    sizes = [[800, [600]], [1024, [768]], [1280, [720, 768]],
             [1366, [768]], [1920, [1080, 1200]]]
    sizes_mobile = [[768, [1024]], [720, [1280]],
                    [768, [1280, 1366]], [1080, [1920]]]
    default_w = 1920
    default_h = 1080
    default_mobile_w = 1080
    default_mobile_h = 1920
    is_mobile = False

    maxw, maxh = get_maximum_screen_resolution()

    if maxw > maxh:
        v_array = sizes
    else:
        v_array = sizes_mobile
        is_mobile = True

    sizew = 0
    sizeh = 0
    for m in v_array:
        if maxw <= m[0]:
            sizew = m[0]
            sizeh = m[1][len(m[1]) - 1]
            for e in m[1]:
                if maxh <= e:
                    sizeh = e
                    break
            break

    if sizew == 0:
        if is_mobile:
            sizew = default_mobile_w
            sizeh = default_mobile_h
        else:
            sizew = default_w
            sizeh = default_h

    return f'{sizew:d}x{sizeh:d}'


def get_image_metadata():
    """
    Get Bing wallpaper metadata.

    :return: XML tag object for the wallpaper image.
    """
    bing_xml_url = get_bing_xml()
    page = urllib.request.urlopen(bing_xml_url)

    bing_xml = ET.parse(page).getroot()

    # For extracting complete URL of the image
    images = bing_xml.findall('image')
    return images[0]


def get_image_url(metadata):
    """
    Get an appropriate Wallpaper URL based on your screen resolution.

    :param metadata: XML tag object with image metadata.
    :return: URL with Bing Wallpaper image.
    """
    base_image = metadata.find("url").text
    # Replace image resolution with the correct resolution
    # from your main monitor
    screen_size = get_screen_resolution_str()
    correct_resolution_image = re.sub(r'\d+x\d+', screen_size, base_image)
    return "https://www.bing.com" + correct_resolution_image


def init_dir(path: pathlib.Path):
    """
    Create directory if it doesn't exist.

    :param path: Path to a directory.
    """
    path.mkdir(parents=True, exist_ok=True)


def p2_dirscan(path):
    files = list()
    size = 0

    for entry in path.iterdir():
        if entry.is_file() and entry.suffix in {'.jpg', '.png'}:
            s = entry.stat().st_size
            files.append((entry, s))
            size = size + s
    files = sorted(files)
    return files, size


def check_limit():
    download_path = get_download_path()
    (files, size) = p2_dirscan(download_path)
    max_size = get_directory_limit()
    while (max_size > 0 and size > max_size and len(files) > 1):
        files[0][0].unlink()
        size = size - files[0][1]
        del files[0]


def wait_for_internet_connection(url, timeout, timeout_urlopen):
    time_start = time.monotonic()
    while True:
        try:
            time_loop = time.monotonic()
            urllib.request.urlopen(url, timeout=timeout_urlopen)
            break
        except Exception as e:
            time_now = time.monotonic()
            if time_now - time_start > timeout:
                raise e

            seconds_sleep = max(0, timeout_urlopen - (time_now - time_loop))
            time.sleep(seconds_sleep)


def show_notification(summary: str, body: str, path_icon: pathlib.Path):
    path_icon = path_icon if path_icon.exists() else None
    app_notification = Notify.Notification.new(summary, str(body), str(path_icon))
    app_notification.show()


def main(force: bool, desktop_environment: str, upscale_fancy: bool):
    """
    Main application entry point.
    """
    app_name = 'Bing Desktop Wallpaper'
    Notify.init(app_name)
    exit_status = 0

    # Setup Notifications
    path_bing_wallpaper = pathlib.Path(__file__).resolve()
    path_icon = path_bing_wallpaper.parent / 'icon.svg'
    if not path_icon.exists():
        # Fallback to set of included icons
        # Likely in development environment
        path_icon = path_bing_wallpaper.parent.parent / 'icon/Bing.svg'

    try:
        wait_for_internet_connection('https://www.bing.com', 1, 2)
    except Exception as err:
        print(err)

        summary = f'Error executing {app_name}'
        body = str(err)
        show_notification(summary, str(body), path_icon)
        sys.exit(1)

    # Determine desktop environment
    if desktop_environment is None:
        desktop_environment = 'gnome'
        source = Gio.SettingsSchemaSource.get_default()
        cinnamon_exists = source.lookup('org.cinnamon.desktop.background', True)
        if cinnamon_exists:
            desktop_environment = 'cinnamon'

    try:
        image_metadata = get_image_metadata()
        image_name = image_metadata.find("startdate").text + ".jpg"
        image_url = get_image_url(image_metadata)

        download_path = get_download_path()
        init_dir(download_path)
        image_path = download_path / image_name

        if not image_path.is_file() or force:
            urllib.request.urlretrieve(image_url, image_path)
            change_background(image_path, desktop_environment)
            change_screensaver(image_path, 'gnome')
            summary = 'Bing Wallpaper updated successfully'
            body = image_metadata.find("copyright").text.encode('utf-8')

            text = str(image_name) + " -- " + str(body) + "\n"
            with open(download_path + "/image-details.txt", "a+") as myfile:
                myfile.write(text)

        elif (
            get_current_background_uri(desktop_environment).exists() and
            get_current_background_uri(desktop_environment).samefile(image_path)
        ):
            summary = 'Bing Wallpaper unchanged'
            body = ('%s already exists in Wallpaper directory' %
                    image_metadata.find("copyright").text.encode('utf-8'))

        else:
            change_background(image_path, desktop_environment)
            change_screensaver(image_path, 'gnome')
            summary = 'Wallpaper changed to current Bing wallpaper'
            body = ('%s already exists in Wallpaper directory' %
                    image_metadata.find("copyright").text.encode('utf-8'))
        check_limit()

        show_notification(summary, str(body), path_icon)
    except Exception as err:
        print(err)

        summary = f'Error executing {app_name}'
        body = str(err)
        show_notification(summary, str(body), path_icon)
        sys.exit(1)

    if upscale_fancy:
        try:
            import shutil
            import skimage.io
            import upscale_arbsr

            path_background = get_current_background_uri(desktop_environment)

            background = skimage.io.imread(path_background)
            background_height = background.shape[0]
            background_width = background.shape[1]

            maxw, maxh = get_maximum_screen_resolution()
            f = max((maxw/background_width), (maxh/background_height))
            maxw, maxh = int(round(background_width*f)), int(round(background_height*f))
            assert maxw > background_width and maxh > background_height
            del background

            path_background_upscaled = pathlib.Path(path_background).parent / \
                (pathlib.Path(path_background).stem + f'_{maxw}x{maxh}.png')

            if (not path_background_upscaled.exists()) or force:
                summary = f'{app_name}: Starting Upscaling'
                body = 'This may take some time'
                show_notification(summary, str(body), path_icon)
                path_upscaled = upscale_arbsr.upscale_cpu(path_background, maxw, maxh)

                shutil.move(path_upscaled, path_background_upscaled)

                summary = f'{app_name}: Successfully upscaled'
                body = f'From {background_width}x{background_height} to {maxw}x{maxh}'
                show_notification(summary, str(body), path_icon)
            else:
                summary = f'{app_name}: Upscaled background already exists'
                body = f'filename: {path_background_upscaled.name}'
                show_notification(summary, str(body), path_icon)

            change_background(str(path_background_upscaled), desktop_environment)
            change_screensaver(str(path_background_upscaled), 'gnome')
        except Exception as err:
            print(err)

            summary = f'Warning {app_name}'
            body = f'Error Upscaling {image_path}\n' + str(err)
            show_notification(summary, str(body), path_icon)

    sys.exit(exit_status)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Automatically downloads and changes desktop wallpaper to Bing Photo of the Day.')
    parser.add_argument('-f', '--force', action='store_true')
    parser.add_argument('-d', '--desktop_environment', default=None)
    parser.add_argument('-u', '--upscale-fancy', action='store_true')
    args = parser.parse_args()

    main(**vars(args))
