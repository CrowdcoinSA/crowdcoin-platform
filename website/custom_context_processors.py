import feedparser
from bs4 import BeautifulSoup
import logging
logger = logging.getLogger(__name__)

def blog_posts(request):
    try:
        print 'called'
        url='http://blog.crowdcoin.co.za/feed'
        feed = feedparser.parse(url)
        items = feed['items'][:5]
        out_put = []
        for item in items:
            soup = BeautifulSoup(item.summary)
            tmp = {'title' : item.title,
            'link' : item.link,
            'tag' : item['tags'][0]['term'],
            'image' : 'https%s' % soup.img.get('src')[4:],
            'summary' : soup.body.text[:150],            }
            out_put.append(tmp)
        return out_put
    except Exception,e:
        logger.warning(e)
        return {'recent_blog_posts':[]}