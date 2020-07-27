import json
import pickle
from posparser import PosParser
from scfg import SimplifiedCFG
import os

class FunctionInfo:

    def __init__(self):
        self.indx = -1
        self.function_name = None
        self.call_position = None
        self.call_offset = None
        self.call_fname = None
        self.source_url = None
        self.script_indx = 999
        self.cfg = None
        self.counter_entered = 0
        self.counter_call = 0
        self.weight = 0
        self.cs_indx = -1

class CallStackInfo:
    def __init__(self, working_dir):
        self.working_dir = working_dir
        self.cs_list = []
        self.func_list = []
        self.sorted_func_list = []
        #self.cfg_list = []

    def check_js_lib(self, source_url):
        JS_LIBRARY = ['jquery','facebook.net','googlesyndication.com','twitter','googletagmanager','pagefair.com',
                      'doubleclick.net','moatads.com','jwplayer','googleapis.com','google-analytics.com',
                      'googletagservices.com']
        for lib in JS_LIBRARY:
            if lib.lower() in source_url:
                return True

        return False

    def save_to_file(self, tmp_dir):
        # func_list
        with open(tmp_dir + '/func_list.log', 'wb') as f:
            pickle.dump(self.func_list, f)

        # cs_list
        output = []
        for cs in self.cs_list:
            index_only_list = [x.indx for x in cs]
            output.append(index_only_list)

        with open(tmp_dir + '/cs_list.log', 'w') as f:
            f.write(json.dumps(output))

        # sorted_func_list
        output = json.dumps([x.indx for x in self.sorted_func_list])
        with open(tmp_dir + '/sorted_func_list.log', 'w') as f:
            f.write(output)

    def load_from_file(self, tmp_dir):
        # func_list
        with open(tmp_dir + '/func_list.log', 'rb') as f:
            self.func_list = pickle.load(f)

        # cs_list
        with open(tmp_dir + '/cs_list.log', 'r') as f:
            data = json.loads(f.read())

        self.cs_list = []
        for item in data:
            cs = [self.func_list[x] for x in item]
            self.cs_list.append(cs)

        # sorted_func_list
        with open(tmp_dir + '/sorted_func_list.log', 'r') as f:
            self.sorted_func_list = json.loads(f.read())

        self.sorted_func_list = [self.func_list[x] for x in self.sorted_func_list]


    def load_callstacks_json(self, json_data):
        import time
        callstacks_json = json_data.split('\n')

        pp = PosParser()
        pp.tmpjs_path = self.working_dir + '/tmp_data/tempjs/'

        for i, callstack_json in enumerate(callstacks_json):
            # print callstack_json
            if callstack_json[0:2] == '[,':
                callstack_json = '[' + callstack_json[2:]

            try:
                items = json.loads(callstack_json)
            except ValueError:
                continue

            callstack = []
            
            for item in items:
                # check if redundant function
                #print len(self.func_list)
                found = False
                for f in self.func_list:
                    if item['position'] == f.call_position and item['source_url'] == f.source_url:
                        callstack.append(f)
                        found = True
                        break

                if found:
                    continue

                # check if the source url is library

                if self.check_js_lib(item['source_url']):
                    continue

                func = FunctionInfo()
                func.indx = len(self.func_list)
                func.function_name = item['function_name']
                func.call_position = item['position']
                func.source_url = item['source_url']
                #func.script_indx = 999
                func.weight = 0
                func.cs_indx = len(self.cs_list)
                func.call_fname = ''

                # parse offset
                # print func.source_url
                try:
                    func.call_offset, func.call_fname = pp.pos_to_off(func.source_url, func.call_position)

                    self.func_list.append(func)
                    callstack.append(func)
                except:
                    # pass
                    print 'callstack source_url error', func.source_url

            if len(callstack) != 0:
                self.cs_list.append(callstack)

    def get_funclist_for_config(self):
        offsets = {}

        for func in self.func_list:
            if func.source_url in offsets:
                offsets[func.source_url].append(func.call_offset)
            else:
                offsets[func.source_url] = [func.call_offset]


        output = []
        for source_url, offset in offsets.iteritems():
            offset = set(offset)
            item = {'source_url': source_url, 'offset': ','.join(offset)}
            output.append(item)

        return output


    def load_cfg_json_list(self, data):
        if self.func_list is None:
            return

        cfg_jsons = data.split('\n')

        for cfg_json in cfg_jsons:
            if cfg_json == '':
                continue

            cfg = SimplifiedCFG()
            ret = cfg.load_from_json(cfg_json)
            if ret == False:
                continue
            #self.cfg_list.append(cfg)

            # link to function list
            for func in self.func_list:
                if func.source_url == cfg.source_url:
                    for call in cfg.trace_calls:
                        if call['pos'] == func.call_offset:
                            func.cfg = cfg
                            break


    def get_callinfo(self, func_indx, func_list):
        sbb_index = None
        func_info = func_list[func_indx]
        if func_info.cfg is None:
            return None, None

        for trace_call in func_info.cfg.trace_calls:
            if trace_call['pos'] == func_info.call_offset:
                sbb_index =func_info.cfg.get_sbb_index(trace_call['id'])
                break

        if sbb_index is None:
            return None, None

        sbb = func_info.cfg.sbbs[sbb_index]
        stmt_index = func_info.cfg.get_stmt_index(sbb, func_info.call_offset)

        return sbb_index, stmt_index









