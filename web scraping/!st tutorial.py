# We import requests so we can load the webpages
import requests
from bs4 import BeautifulSoup as bs


# load Our first Page

# Load the webpage content
r = requests.get("https://keithgalli.github.io/web-scraping/example.html")

# Convert our webpage to a beautiful soup object
soup = bs(r.content)

print(soup)
