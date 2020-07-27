from callstackinfo import CallStackInfo
from controlflowfuzzer import ControlFlowFuzzer
from weightcalculator import WeightCalculator
import subprocess, os
from threading import Timer
import psutil
import time
import math
import page_cluster

this_dir, this_filename = os.path.split(__file__)
PUPPET_RUN_PATH = this_dir + '/node/run_puppet.js'

class JsConFuzzer:

    def __init__(self, test_js, working_dir, chrome_path, domain=None, rename_dyn = True, stat_mode = False):
        self.csi = CallStackInfo(working_dir)
        self.test_js = test_js
        self.rename_dyn = rename_dyn
        self.callstacks = None
        self.confuzzer = ControlFlowFuzzer(self, rename_dyn=rename_dyn)
        self.domain = domain
        self.chrome_path = chrome_path
        self.stat_mode = stat_mode
        self.null_confuzz = False
        self.stat = {'stat':'', 'runtime':0.0, 'runtime2':0.0, 'count':0, 'count2':0}

        self.TMP_PATH = working_dir + '/tmp_data/'
        self.CONFIG_FILE_PATH = self.TMP_PATH+ 'v8mod.cfg'
        self.CALLSTACK_LOG_PATH = self.TMP_PATH + 'callstacks.log'

        if not os.path.exists(self.TMP_PATH):
            os.makedirs(self.TMP_PATH)
        if not os.path.exists(self.TMP_PATH + 'html'):
            os.makedirs(self.TMP_PATH + 'html')
        if not os.path.exists(self.TMP_PATH + 'screenshot'):
            os.makedirs(self.TMP_PATH + 'screenshot')
        if not os.path.exists(self.TMP_PATH + 'tempjs'):
            os.makedirs(self.TMP_PATH + 'tempjs')

    #chrome_config = {'trace_mode':False, 'fuzz_mode':False, 'data':[]}

    def load_callstack_json(self, data):
        return self.csi.load_callstacks_json(data)

    def load_callstack_file(self, filename):
        with open(filename, 'r') as f:
            data = f.read()
            return self.csi.load_callstacks_json(data)

    def create_config_file(self, data=[], trace_mode = False, fuzz_mode = False, rename_dyn = False, stat_mode = None):
        if stat_mode is None:
            stat_mode = self.stat_mode

        output = ''
        output += 'trace=' + ('1' if trace_mode else '0') + '\n'
        output += 'cfmod=' + ('1' if fuzz_mode else '0') + '\n'
        output += 'rename=' + ('1' if rename_dyn else '0') + '\n'
        output += 'stat=' + ('1' if stat_mode else '0') + '\n'
        output += '\n'

        for item in data:
            output += item['source_url'] + '\n'
            output += item['offset'] if trace_mode else 'none'
            output += '\n'
            output += item['fuzz_data'] if fuzz_mode else 'none'
            output += '\n'
            output += '\n'

        with open(self.CONFIG_FILE_PATH, 'w') as f:
            f.write(output)


    def load_trace_log(self, filename):
        # simply separate w/ grep
        cat = subprocess.Popen(['cat',filename], stdout = subprocess.PIPE)
        grep1 = subprocess.Popen(['grep','{"function_name":'], stdin = cat.stdout, stdout = subprocess.PIPE)
        cfgs = grep1.communicate()[0]
        #print cfgs
        self.csi.load_cfg_json_list(cfgs)

        cat = subprocess.Popen(['cat', filename], stdout=subprocess.PIPE)
        grep2 = subprocess.Popen(['grep','>>'], stdin = cat.stdout, stdout = subprocess.PIPE)
        sort = subprocess.Popen(['sort',], stdin=grep2.stdout, stdout=subprocess.PIPE)
        uniq = subprocess.Popen(['uniq', '-c'], stdin=sort.stdout, stdout=subprocess.PIPE)

        tracecnt = uniq.communicate()[0]
        #print tracecnt
        tracecnt = tracecnt.split('\n')

        total_trace = 0
        # parse trace count
        for line in tracecnt:
            if line == '':
                continue

            try:
                data = line.split('>>')
                cnt = int(data[0])
                type = data[1].split('=')[0]
                data = data[1].split('[')[1][:-1]
                data = data.split('|')
                script_id = data[0]
                function_id = data[1]
                if type == 'FC':
                    call_offset = data[2]
                total_trace+=1
            except:
                continue

            # find this function
            for func in self.csi.func_list:
                if func.cfg == None:
                    continue

                if func.cfg.script_id == script_id and func.cfg.function_id == function_id:
                    if type == 'FC':
                        if func.call_offset == call_offset:
                            func.counter_call = cnt
                            break
                    elif type == 'FE':
                        func.counter_entered = cnt
                        break

        return total_trace


    def launch_puppet(self, mode, timeout_sec = None, kill_if_event = False, output_filename = None):

        def kill_puppet(proc):
            process = psutil.Process(proc.pid)
            for proc2 in process.children(recursive=True):
                proc2.kill()
            process.kill()

            #proc.terminate()

        def comm_realtime(proc):
            while True:
                line = proc.stdout.readline().rstrip()
                if not line:
                    break
                yield line

        cmd = ['node', PUPPET_RUN_PATH, self.chrome_path, self.TMP_PATH, self.test_js, str(mode)]
        if output_filename is not None:
            cmd.append(output_filename)

        # print cmd

        run = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = ''
        timer = None



        if timeout_sec is not None:
            timer = Timer(timeout_sec, kill_puppet, [run])
            timer.start()
        try:
            if kill_if_event:
                for out in comm_realtime(run):
                    # print out
                    output += out + '\n'
                    if 'EVENT HAPPENED' in out:
                        # print '>> Event Happened :Terminate browser'
                        time.sleep(1)
                        kill_puppet(run)
                        break
            else:
                output, err = run.communicate()
        finally:
            if timer is not None:
                timer.cancel()


        return output

    def run_clean(self, timeout=None):
        self.create_config_file([])
        self.launch_puppet(2, timeout_sec=timeout)


    def run_get_callstack(self, print_callstack = True, timeout = None):
        self.create_config_file([], rename_dyn=self.rename_dyn)

        if self.stat_mode:
            callstacks_json = self.launch_puppet(0, timeout_sec=timeout, kill_if_event=True)
            callstacks_json, self.stat['stat'], self.stat['runtime'], self.stat['count'], self.stat['runtime2'] = self.filter_stat_out(callstacks_json)
            cs = callstacks_json.split('\n')
            # if len(cs) > 50:
            #     callstacks_json = '\n'.join(cs[0:50])
        else:
            callstacks_json = self.launch_puppet(0, timeout_sec=timeout)

        if print_callstack:
            print callstacks_json

        with open(self.CALLSTACK_LOG_PATH, 'w') as f:
            f.write(callstacks_json)



        self.csi.load_callstacks_json(callstacks_json)

        self.save_to_file()



    def load_callstack_from_file(self):
        with open(self.CALLSTACK_LOG_PATH, 'r') as f:
            callstacks_json = f.read()

        if self.stat_mode:
            callstacks_json, self.stat['stat'], self.stat['runtime'] = self.filter_stat_out(callstacks_json)
            cs = callstacks_json.split('\n')
            #if len(cs) > 5:
            #    callstacks_json = '\n'.join(cs[0:5])

        print callstacks_json

        self.csi.load_callstacks_json(callstacks_json)

        self.save_to_file()


    def load_from_file(self):
        self.csi.load_from_file(self.TMP_PATH)

    def save_to_file(self):
        self.csi.save_to_file(self.TMP_PATH)

    def run_get_trace(self, print_stack = False, timeout = None):
        if len(self.csi.func_list) == 0:
            print "callstack data is not available"
            return False

        self.create_config_file(self.csi.get_funclist_for_config(), trace_mode=True, rename_dyn=self.rename_dyn)

        if self.stat_mode:
            output = self.launch_puppet(1, timeout_sec=timeout, output_filename='original', kill_if_event=True)
        else:
            output = self.launch_puppet(1, timeout_sec=timeout, output_filename='original')
        #print 'browser closed'

        with open('trace.log', 'w') as f:
            f.write(output)


        total_trace = self.load_trace_log('trace.log')
        # self.load_script_trace()
        self.calculate_weight()
        self.save_to_file()

        if print_stack:
            self.print_func_list_info()

        if self.stat_mode:
            output, self.stat['stat'], self.stat['runtime'], tmp, tmp1 = self.filter_stat_out(output)
            self.stat['count'] = len(self.csi.func_list)
            self.stat['count2'] = total_trace

    def load_script_trace(self):
        script_list = []
        with open('script_load.log', 'r') as f:
            data = f.readlines()
            for line in data:
                script_list.append(line[0:-1])

        for func in self.csi.func_list:
            if func.source_url in script_list:
                func.script_indx = script_list.index(func.source_url)



    def print_func_list_info(self):
        for func in self.csi.func_list:
            if func.cfg is not None:
                print ','.join([func.function_name, func.source_url, str(func.counter_entered), str(func.counter_call), str(func.call_offset)])
                # func.cfg.draw()
                # raw_input()
            else:
                print func.function_name + ',' + '-1,-1'+ ',' + str(func.call_offset)

    def print_callstack_info(self):
        for i, cs in enumerate(self.csi.cs_list):
            print '<<Callstack ' + str(i) + '>>'
            for func in cs:
                if func.cfg is not None:
                    print func.function_name + ',' + str(func.counter_entered) + ',' + str(func.counter_call) + ',' + str(func.call_offset)
                    # func.cfg.draw()
                    # raw_input()
                else:
                    print func.function_name + ',' + '-1,-1'+ ',' + str(func.call_offset)

            print '\n'

    def run_tampering_check(self, test_id, jft=None):
        self.confuzzer.fuzz_funclist = self.csi.sorted_func_list
        proposals = self.confuzzer.generate_proposals()
        if jft:
            print 'Initializing session...'
            jft.run_init_session_script()

        self.confuzzer.start_tampering_testing([proposals[test_id]], no_output=True)

    def run_confuzz(self, batch_cnt=10, start_index=-1, count=-1, fuzz_mode='disable', timeout = None, kill_if_event=False, jft=None):
        self.confuzzer.fuzz_funclist = self.csi.sorted_func_list
        self.confuzzer.timeout = timeout
        self.confuzzer.kill_if_event = kill_if_event

        proposals = self.confuzzer.generate_proposals()
        if start_index != -1:
            if count != -1:
                proposals = proposals[start_index:start_index + count]
            else:
                proposals = proposals[start_index:]

        total_it = int(math.ceil(len(proposals) / batch_cnt))

        for i in range(0, total_it):
            print '[ Tampering Test Batch ', i+1, '/', total_it,']'
            if jft:
                print 'Initializing session...'
                jft.run_init_session_script()
            cur_proposals = proposals[batch_cnt * i:batch_cnt*(i+1)]
            self.confuzzer.start_tampering_testing(cur_proposals)

            start_id = cur_proposals[0]['id']
            cur_prop_cnt = len(cur_proposals)

            print '\nClustering test results...'
            page_cluster.perform_clustering(self.TMP_PATH, int(start_id), cur_prop_cnt)

            print 'Check any screenshot file in each cluster to see if tampering succeed'

            cont = True
            while True:
                ans = raw_input('continue (y/n)? ')
                if ans.lower() == 'n':
                    cont = False
                    break
                elif ans.lower() == 'y':
                    break

            if not cont:
                break

    def calculate_weight(self):
        self.csi.sorted_func_list = self.csi.func_list
        wc = WeightCalculator(self.csi, self.domain)
        wc.calculate(False)


    def run_getstat(self, timeout = None):
        self.create_config_file([], rename_dyn=self.rename_dyn, stat_mode = True)
        output = self.launch_puppet(3, kill_if_event=True, timeout_sec = timeout)
        output, self.stat['stat'], self.stat['runtime'], tmp, tmp1 = self.filter_stat_out(output)
        return self.stat['stat'], self.stat['runtime']

    def filter_stat_out(self, output, no_need_output = False):
        new_out = []
        stat = ''
        runtime = 0.0
        evt_cnt = 0
        evt_runtime = 0.0
        for line in output.split('\n'):
            #print line
            pos = line.find('>>STAT:')
            if pos != -1:
                stat = line[pos + 7:]
                continue

            pos = line.find('>>RUNTIME:')
            if pos != -1:
                runtime = float(line[pos + 10:])
                continue

            pos = line.find('>>EVENT_INFO:')
            if pos != -1:
                tmp = line[pos + 13:].split(',')
                evt_cnt = int(tmp[0])
                evt_runtime = float(tmp[1])
                continue

            new_out.append(line)

        if no_need_output:
            return stat, runtime, evt_cnt, evt_runtime
        else:
            return '\n'.join(new_out), stat, runtime, evt_cnt, evt_runtime


    def print_full_stat(self, short_mode = True):
        # #of js
        js_dict = dict()
        func_cnt = len(self.csi.func_list)
        branch_cnt = 0
        sbb_cnt = 0
        for func in self.csi.func_list:
            js_dict[func.source_url] = 1
            if func.cfg is None:
                continue
            sbb_cnt += len(func.cfg.sbbs)

            for sbb in func.cfg.sbbs:
                for st in sbb['statements']:
                    if st['node_type'] in ['8','12','34']:
                        branch_cnt += 1

        if short_mode:
            print ','.join(
                [str(len(js_dict)), str(func_cnt), str(branch_cnt)])
        else:
            print '# of js : ', len(js_dict)
            print '# of func : ', func_cnt
            print '# of branches : ', branch_cnt
            print '# of callstacks : ', len(self.csi.cs_list)
            print '# of sbb : ', sbb_cnt


    def print_confuzz_trials(self, weighted = True, fuzz_mode='disable'):
        if weighted:
            self.confuzzer.fuzz_funclist = self.csi.sorted_func_list
        else:
            self.confuzzer.fuzz_funclist = self.csi.func_list

        proposals = self.confuzzer.generate_proposals()
        TP_MODE = ['NOT APPLIED', 'DISABLE', 'FORCED EXEC.', 'REPEAT']
        for proposal in proposals:
            cfg = proposal['cfg']
            tp_data = cfg['fuzz_data'].split(':')

            setting = '<Offset: %s, Branch Indx: %s, Tampering Mode: %s, Opt.: %s' \
                      % (tp_data[0], tp_data[1], TP_MODE[int(tp_data[2])], tp_data[3])
            print 'ID: %s, Func. Name: %s, Func. ID: %s, Source URL: %s, Tampering Setting: %s' \
                  % (proposal['id'], proposal['function_name'], proposal['fuid'], cfg['source_url'], setting)


    def run_confuzz_for_stat(self, timeout=None):
        if len(self.csi.func_list) == 0:
            return

        offset = self.csi.func_list[0].call_offset
        config = dict()
        config['source_url'] = self.csi.func_list[0].source_url
        config['fuzz_data'] = offset + ':0:1:0'
        self.create_config_file([config], fuzz_mode=True, rename_dyn=self.rename_dyn)
        output = self.launch_puppet(2, kill_if_event=True, timeout_sec=timeout)
        self.stat['stat'], self.stat['runtime'], tmp, tmp1 = self.filter_stat_out(output, True)




    def printFeatures(self):
        wc = WeightCalculator(self.csi, self.domain)
        wc.getFeatures()


