# Thunder-LLM-Crawl

## Setup

```bash
sudo apt install net-tools # for ifconfig

# Installation of chrome
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor -o /usr/share/keyrings/google-linux.gpg

echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux.gpg] http://dl.google.com/linux/chrome/deb/ stable main' | \
sudo tee /etc/apt/sources.list.d/google-chrome.list

sudo apt update
sudo apt install google-chrome-stable -y

git clone https://github.com/mcrl/Thunder-LLM-crawl.git
cd Thunder-LLM-crawl
pip install -r requirements.txt

python scripts/install/install_chromedriver.py
```

All crawled data and cache file will be saved to `data`, `cache` directory, respectively.
If you want to specify other path, please make a symbolic link for this.

```bash
ln -s /path/to/data/dir data
ln -s /path/to/cache/dir cache
```

Finally, setup env file to `configs/env.yml`.

## Naver Kin

### Writing configuration files

First, you need to obtain Kin user list

```bash
python scripts/kin/kin_find_users.py --ip "your.ip.add.ress" --chromedriver /path/to/chromedriver
```

This script will save users to `scripts/kin/kin_users.txt`

Then, write the configuration file as described in `configs/kin/kin_sample.yml`.
List all users to scrap in a text file(as shown in `configs/kin/kin_userlist_sample.txt`) and specify the text path to config file.



### Executing Crawler

```bash
python scripts/kin/kin_crawl.py --config path/to/kin/config.yml
# See configs/kin/kin_smaple.yml for config file example.
```


## Naver News

First, collect supported content providers by running:

```bash
python scripts/news/get_news_list.py
```

See `navernews_available.txt` file for content providers in NaverNews.

Then, fix the configuration file: `configs/daumnews/config.yml`. Specify the date range and content providers to collect.

> Add content providers to collect(list in `navernews_available.txt`)

Executing Crawler

``` bash
python downloader.py --task navernews --config ./configs/navernews/config.yml
```

## Naver Blog

First, collect the blog IDs by running:

```bash 
python naverblog/collect_blogs.py --config ./configs/naverblog/config.yml
```

To execute the crawler, run:

``` bash
python downloader.py --task naverblog --config ./configs/naverblog/config.yml
```


## Naver Cafe

First, collect the cafe IDs by running:

```bash 
# see configs/cafelist/navercafe_sample.yml for sample
python downloader.py --task navercafe_id --config ./configs/cafelist/config.yml
```

Then, build the list of cafe IDs from the collected data:

```bash
python scripts/navercafe/build_navercafe_id.py
```
This script will create a list of cafe IDs at `configs/navercafe/navercafe_id.tsv`.

Make sure that the 'cafelist' field in the configuration file at `configs/navercafe/config.yml` is set to the path above.

To execute the crawler, run:

``` bash
python downloader.py --task navercafe --config ./configs/navercafe/config.yml
```


## Daum News

First, collect supported content providers by running:

```bash
python scripts/news/get_news_list.py
```

See `daumnews_available.txt` file for supported content providers.
We collected data from daumnews to supplement more content that are not provided in NaverNews service.
Thus, we excluded collecting contents that are proivded in Naver  see `navernews_available.txt` file for content providers in NaverNews.

Then, fix the configuration file: `configs/daumnews/config.yml`. Specify the date range and content providers to collect.

> Add content providers to collect(list in `daumnews_available`). Specify content providers to exclude (list in `navernews_available.txt`)

To execute the crawler, run:

``` bash
python downloader.py --task daumnews --config ./configs/daumnews/config.yml
```


## Daum Cafe

We need google search API key and your custom search engine.
Refer [official homepage](https://programmablesearchengine.google.com/about/) for getting started.
Get search API key and your custom search engine id and write them to the configuration file.

Then, collect the cafe IDs by running:

```bash 
# see configs/cafelist/daumcafe_sample.yml for sample
python downloader.py --task daumcafe_id --config ./configs/cafelist/config.yml
```

Then, build the list of cafe IDs from the collected data:

```bash
python scripts/daumcafe/daumcafe_id.py
```
This script will create a list of cafe IDs at `configs/daumcafe/daumcafe.txt`.

Make sure that the 'cafelist' field in the configuration file at `configs/daumcafe/config.yml` is set to the path above.

To execute the crawler, run:
``` bash
python downloader.py --task daumcafe --config ./configs/daumcafe/config.yml
```
