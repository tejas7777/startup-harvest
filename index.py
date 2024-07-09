import requests
from bs4 import BeautifulSoup
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import OrderedDict

'''

Code To Scrape eu-startups.com

'''

directory_url = "https://www.eu-startups.com/directory/"

def scrape_countries(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("[scrape_countries][error]:",e)
        return []
    soup = BeautifulSoup(response.text, 'html.parser')

    country_list_container = soup.find('div', id='wpbdp-categories')

    if not country_list_container:
        print("scrape_countries][country_list_container_not_found]")
        return []
    
    country_list_items = country_list_container.find_all('li')
    
    countries = []

    for item in country_list_items:
        link = item.find('a')
        if link:
            country_name = link.text.strip()
            country_url = link['href']
            countries.append({'name': country_name, 'url': country_url})
    
    return countries

def scrape_startups(url):
    startups = []

    max_depth = 0

    while url and max_depth < 1000:
        try:
            response = requests.get(url)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching the page: {e}")
            return startups

        soup = BeautifulSoup(response.text, 'html.parser')
        
        startup_list_container = soup.find('div', id='wpbdp-listings-list')
        
        if not startup_list_container:
            print("[scrape_startups]: startup not found")
            return startups
        
        startup_list_items = startup_list_container.find_all('div', class_='wpbdp-listing')

        for item in startup_list_items:
            if item == None:
                continue

            title_element = item.find('h3') 
            link_element = item.find('a')
            description_element = item.find('div', class_='listing-title')

            thumbnail_container = item.find('div', class_='listing-thumbnail')
            thumbnail_element = thumbnail_container.find('img') if thumbnail_container else None

            business_name_container = item.find('div', class_='wpbdp-field-business_name')
            business_name_element = business_name_container.find('div', class_='value') if business_name_container else None

            category_container = item.find('div', class_='wpbdp-field-category')
            category_sub_container = category_container.find('div', class_='value') if category_container else None
            category_element = category_sub_container.find('a') if category_sub_container else None

            location_container = item.find('div', class_='wpbdp-field-based_in')
            location_element = location_container.find('div', class_='value') if location_container else None

            tags_container = item.find('div', class_='wpbdp-field-tags')
            tags_element = tags_container.find('div', class_='value') if tags_container else None

            founded_container = item.find('div', class_='wpbdp-field-founded')
            founded_element = founded_container.find('div', class_='value') if founded_container else None
            
            startup_data = {}
            if title_element:
                startup_data['title'] = title_element.text.strip()
            if link_element:
                startup_data['link'] = link_element['href']
            if description_element:
                startup_data['description'] = description_element.text.strip()
            if thumbnail_element:
                startup_data['thumbnail'] = thumbnail_element['src']
            if business_name_element:
                startup_data['business_name'] = business_name_element.text.strip()
            if category_element:
                startup_data['category'] = category_element.text.strip()
            if location_element:
                startup_data['location'] = location_element.text.strip()
            if tags_element:
                startup_data['tags'] = tags_element.text.strip()
            if founded_element:
                startup_data['founded'] = founded_element.text.strip()

            if link_element:
                additional_data = scrape_additional_startup_data(link_element['href'])

                startup_data["data"] = additional_data
            
            startups.append(startup_data)
        
        next_page = soup.find('link', {'rel': 'next'})

        if next_page:
            print(f"[scrape_startup][next_page]", next_page["href"])
            url = next_page['href']
            max_depth += 1
        else:
            url = None

    return startups

def scrape_additional_startup_data(url):

    try:
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        additional_data = {}

        business_desc_element = soup.find('div', class_='wpbdp-field-long_business_description').find('div', class_='value') if soup.find('div', class_='wpbdp-field-long_business_description') else None
        if business_desc_element is None:
            business_desc_element = soup.find('div', class_='wpbdp-field-business_description').find('div', class_='value') if soup.find('div', class_='wpbdp-field-business_description') else None
        total_funding_element = soup.find('div', class_='wpbdp-field-total_funding').find('div', class_='value') if soup.find('div', class_='wpbdp-field-total_funding') else None
        founded_element = soup.find('div', class_='wpbdp-field-founded').find('div', class_='value') if soup.find('div', class_='wpbdp-field-founded') else None
        website_element = soup.find('div', class_='wpbdp-field-website').find('div', class_='value') if soup.find('div', class_='wpbdp-field-website') else None
        status_element = soup.find('div', class_='wpbdp-field-company_status').find('div', class_='value') if soup.find('div', class_='wpbdp-field-company_status') else None
        linkedin_element = soup.find('div', class_='social-field linkedin').find('a')['href'] if soup.find('div', class_='social-field linkedin') else None

        if business_desc_element:
            additional_data['business_description'] = business_desc_element.text.strip()
        if business_desc_element:
            additional_data['long_business_description'] = business_desc_element.get_text(separator="\n").strip()
        if total_funding_element:
            additional_data['total_funding'] = total_funding_element.text.strip()
        if founded_element:
            additional_data['founded'] = founded_element.text.strip()
        if website_element:
            additional_data['website'] = website_element.text.strip()
        if status_element:
            additional_data['status'] = status_element.text.strip()
        if linkedin_element:
            additional_data['linkedin'] = linkedin_element

        return additional_data
    
    except Exception as e:

        print("[scrape_additional_startup_data][error]", e)
        return {}

if __name__ == '__main__':
    data = {}
    countries = scrape_countries(directory_url)
    
    def process_country(country):
        print(f"Country: {country['name']}, URL: {country['url']}")
        startups = scrape_startups(country['url'])
        return country['name'], startups
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_country, country) for country in countries]
        
        for future in as_completed(futures):
            country_name, startups = future.result()
            data[country_name] = startups

    with open('../data/data.json', 'w') as fp:
        data = OrderedDict(sorted(data.items()))
        json.dump(data, fp)
        print("Data Saved")