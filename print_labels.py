import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
import bluetooth
import os
import time
import PIL.Image
import image_helper

# Bluetooth address of the target device
MAC_ADDRESS_OF_PRINTER = "AB:52:6B:23:8E:6E"


def download_images(api_key, ids):
    # Set the download directory as the source directory where the code is launched from
    download_directory = os.path.abspath(os.path.dirname(__file__))

    # Set up the path to the Chrome profile directory
    profile_directory = os.path.join(download_directory, "ChromeProf")

    # Set up Chrome options with --user-data-dir
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument(f"--user-data-dir={profile_directory}")  # Use the Chrome profile directory

    # Set up Chrome options for headless browsing and download settings
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless")  # Run in headless mode (no GUI)
    # Disable the sandbox mode for Linux
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration
    # Disable software rasterizer
    chrome_options.add_argument("--disable-software-rasterizer")
    # Disable /dev/shm usage for Linux
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-extensions")  # Disable extensions
    chrome_options.add_argument("--disable-infobars")  # Disable infobars
    chrome_options.add_argument(
        "--disable-notifications")  # Disable notifications
    chrome_options.add_argument(
        "--disable-popup-blocking")  # Disable popup blocking
    # Disable password saving popup
    chrome_options.add_argument("--disable-save-password-bubble")
    # Disable translation prompt
    chrome_options.add_argument("--disable-translate")
    chrome_options.add_argument(
        "--disable-web-security")  # Disable web security
    # Disable phishing detection
    chrome_options.add_argument("--disable-client-side-phishing-detection")
    chrome_options.add_argument(
        "--disable-default-apps")  # Disable default apps
    # Disable syncing to Google account
    chrome_options.add_argument("--disable-sync")
    # Disable background networking
    chrome_options.add_argument("--disable-background-networking")
    # Disable timer throttling
    chrome_options.add_argument("--disable-background-timer-throttling")
    # Disable backgrounding of occluded windows
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-breakpad")  # Disable crash reports
    # Disable component updates
    chrome_options.add_argument("--disable-component-update")
    # Disable domain reliability monitoring
    chrome_options.add_argument("--disable-domain-reliability")
    # Disable certain features
    chrome_options.add_argument(
        "--disable-features=TranslateUI,BlinkGenPropertyTrees")
    # Disable IPC flooding protection
    chrome_options.add_argument("--disable-ipc-flooding-protection")
    # Disable renderer backgrounding
    chrome_options.add_argument("--disable-renderer-backgrounding")
    # Disable renderer throttling
    chrome_options.add_argument("--disable-renderer-throttling")
    # Disable site isolation for policy
    chrome_options.add_argument("--disable-site-isolation-for-policy")
    # Disable software rasterizer
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-voice-input")  # Disable voice input
    chrome_options.add_argument(
        "--disable-wake-on-wifi")  # Disable wake on WiFi
    # Disable implementation-side painting
    chrome_options.add_argument("--disable-impl-side-painting")
    # Disable DNS prefetching
    chrome_options.add_argument("--dns-prefetch-disable")
    # Use basic password storage
    chrome_options.add_argument("--password-store=basic")
    chrome_options.add_argument("--disable-features=MultipleDownloadFiles")
    prefs = {
        "profile.content_settings.exceptions.automatic_downloads.*.setting" : 1,
        "profile.default_content_setting_values.automatic_downloads": 1,
        "download.default_directory": download_directory,
    }
    chrome_options.add_experimental_option("prefs", prefs)


    # Create a Chrome WebDriver with the specified options
    chromedriver_path = "path/to/chromedriver"  # Path to chromedriver executable
    driver = webdriver.Chrome(service=ChromeService(executable_path=chromedriver_path),
                              options=chrome_options)

    # Navigate to the website
    ids = [str(id) for id in ids]
    url = f"https://slugs.bssl.binghamtonsa.org/equipment/{','.join(ids)}/printLabel/"
    print("Finding and downloading labels...")
    driver.get(url)
    

    time.sleep(5)

    driver.quit()


def print_found_labels():

    print("Connecting to printer via bluetooth")

    # RFCOMM channel number for the connection
    rfcomm_channel = 1

    # Connect to the Bluetooth device
    sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    sock.connect((MAC_ADDRESS_OF_PRINTER, rfcomm_channel))
    print("Connected... Initializing printer")
    header(sock)

    # Find all .png files in the current directory
    png_files = [f for f in os.listdir('.') if f.endswith('.png')]

    # Call print_image on each .png file
    for filename in png_files:
        print(f"Printing {filename}...")
        print_image(sock, filename)

        # Remove the file after printing
        os.remove(filename)
    sock.close()


def header(port):
    # printer initialization sniffed from Android app "Print Master"
    packets = [
        '1f1138',
        '1f11121f1113',
        '1f1109',
        '1f1111',
        '1f1119',
        '1f1107',
        '1f110a1f110202'
    ]

    for packet in packets:
        port.send(bytes.fromhex(packet))
        # port.flush()


def print_image(port, filename):
    width = 96

    with PIL.Image.open(filename) as src:
        # Rotate the image 90 degrees
        src = src.rotate(90, expand=True)

        image = image_helper.preprocess_image(src, width)

    # printer initialization sniffed from Android app "Print Master"
    output = '1f1124001b401d7630000c004001'

    # adapted from https://github.com/theacodes/phomemo_m02s/blob/main/phomemo_m02s/printer.py
    for chunk in image_helper.split_image(image):
        output = bytearray.fromhex(output)

        bits = image_helper.image_to_bits(chunk)
        for line in bits:
            for byte_num in range(width // 8):
                byte = 0
                for bit in range(8):
                    pixel = line[byte_num * 8 + bit]
                    byte |= (pixel & 0x01) << (7 - bit)
                output.append(byte)

        port.send(output)
        output = ''


if __name__ == '__main__':
    # Check if the correct number of arguments are provided
    if len(sys.argv) != 3:
        print("Usage: python script_name.py <api_key> <ids>")
        sys.exit(1)

    # Get the API key and IDs from command line arguments
    api_key = sys.argv[1]
    ids = sys.argv[2].split(',')

    # Convert IDs from strings to integers
    try:
        ids = list(map(int, ids))
    except ValueError:
        print("Error: IDs must be integers")
        sys.exit(1)

    # Call the download_images function with the API key and IDs
    download_images(api_key, ids)

    # Call the print_found_labels function with the IDs
    # try:
    print_found_labels()
    # except e:
    #     print("Error: Could not connect to printer", e)
    #     sys.exit(1)