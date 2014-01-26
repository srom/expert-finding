expert-finding
==============

Implementation of the paper ["Choosing the right crowd: expert finding in social networks"](http://www.edbt.org/Proceedings/2013-Genova/papers/edbt/a57-bozzon.pdf)  [ A Bozzon, M Brambilla, S Ceri, M Silvestri, Giuliano Vesci. 2013 ] for Instagram's network.

### Dependencies

 - Python 2.7
 - peewee: http://peewee.readthedocs.org/en/latest/index.html
 - python-instagram: https://github.com/Instagram/python-instagram
 - AlchemyAPI: https://pypi.python.org/pypi/AlchemyAPI
 - Requests: http://docs.python-requests.org/en/latest/
 - nltk: http://nltk.org/

### Extend

You can easily add another crawler (e.g Twitter crawler) by extending the class Crawler. See [instagram_crawler.py](https://github.com/srom/expert-finding/blob/master/instagram_crawler.py) for a working example of a class extending Crawler.
