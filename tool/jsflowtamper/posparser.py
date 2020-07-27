from pos_to_off import pos_to_offset
import urllib2
import requests
from os import system

class PosParser:
    sources = {}
    tmpjs_path = ''

    def pos_to_off(self, source_url, position):
        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36' ,
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3' ,
            'accept-language': 'en-US,en;q=0.9,ko;q=0.8'
        }

        # download file if not exist
        data = None
        # print source_url
        if source_url in self.sources:
            data = self.sources[source_url]
        else:
            if source_url[:4] == 'http':
                # download js file
                try:
                    req = urllib2.Request(source_url, headers = headers)
                    response = urllib2.urlopen(req, timeout = 5)
                    js = response.readlines()
                except:
                    try:
                        res = requests.get(source_url, headers = headers, timeout = 5)
                        js = res.text.split('\n')
                    except:
                        # download via command
                        ret = system('wget -O /tmp/tmp.js ' + source_url)
                        if ret == 0:
                            with open('/tmp/tmp.js', 'r') as f:
                                js = f.readlines()
                        else:
                            raise




            elif source_url[:4] == 'file':
                # read from tempjs file
                with open(source_url[7:], 'r') as f:
                    js = f.readlines()
            else:
                # read from tempjs file
                with open(self.tmpjs_path + source_url, 'r') as f:
                    js = f.readlines()

            data = js

            try:
                data = [line.decode('utf-8', errors='replace') for line in data]
            except:
                data = js

            self.sources[source_url] = data

        line, column = position.split(':')
        line = int(line)
        column = int(column)
        offset = pos_to_offset(data, line, column)


        # get call function name

        data_line = data[line - 1]
        fname = ''
        line_len = len(data_line)
        for i in range(column-1, line_len):
            c = data_line[i]
            if c.isalnum() or c in ['.','_']:
                fname += c
            else:
                break


        #fname =''




        return str(offset), fname