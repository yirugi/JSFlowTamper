
class ControlFlowFuzzer:
    def __init__(self, jscon, rename_dyn = False):
        self.jscon = jscon
        self.csi = jscon.csi

        self.fuzz_mode = 1
        self.branch = 0
        self.optional = 0

        self.rename_dyn = rename_dyn

        self.config_list = []

        self.fuzz_funclist = jscon.csi.sorted_func_list

        self.print_log = True

        self.timeout = None
        self.kill_if_event = False


    def get_cur_func(self):
        return self.fuzz_funclist[self.funclist_index]

    def get_cur_sbb(self):
        return self.fuzz_funclist[self.funclist_index].cfg.sbbs[self.sbb_index]

    def get_cur_stmt(self):
        return self.fuzz_funclist[self.funclist_index].cfg.sbbs[self.sbb_index]['statements'][self.stmt_index]


    def get_fuzz_config(self):
        if self.fuzz_mode == 3:
            self.optional = 5000

        offset = self.get_cur_stmt()['position']
        config = dict()
        config['source_url'] = self.get_cur_func().source_url

        if self.jscon.null_confuzz:
            config['fuzz_data'] = str(offset) + ':' + str(self.branch) + ':' + str(0) + ':' + str(
                self.optional)
        else:
            config['fuzz_data'] =  str(offset) + ':' + str(self.branch) + ':' + str(self.fuzz_mode) + ':' + str(self.optional)

        return config

    def move_to_next_func(self):
        return self.set_func_callpoint(self.funclist_index + 1)



    def set_func_callpoint(self, funclist_index):
        if funclist_index == len(self.fuzz_funclist):
            return False

        sbb_index, stmt_index = self.csi.get_callinfo(funclist_index, self.fuzz_funclist)
        if sbb_index is None or stmt_index is None:
            #print 'Failed getting call information'
            return False

        self.funclist_index = funclist_index
        self.sbb_index = sbb_index
        self.stmt_index = stmt_index

        return True


    def start_tampering_testing(self, proposals, no_output=False):
        TP_MODE = ['NOT APPLIED','DISABLE','FORCED EXEC.','REPEAT']
        for proposal in proposals:
            cfg = proposal['cfg']
            tp_data = cfg['fuzz_data'].split(':')

            setting = '<Offset: %s, Branch Indx: %s, Tampering Mode: %s, Opt.: %s>' \
                      % (tp_data[0], tp_data[1], TP_MODE[int(tp_data[2])], tp_data[3])
            print 'ID: %s, Tampering Setting: %s, Func. Name: %s, Func. Offset: %s, Source URL: %s, ' \
                  % (proposal['id'], setting, proposal['function_name'], proposal['fuid'],cfg['source_url'])

            # start test
            self.jscon.create_config_file([cfg], fuzz_mode=True, rename_dyn=self.rename_dyn)
            if no_output:
                output_filename = None
            else:
                output_filename = 'test' + '{:04}'.format(int(proposal['id']))
            output = self.jscon.launch_puppet(2, self.timeout, kill_if_event=self.kill_if_event,
                                              output_filename=output_filename)
            if 'EVENT HAPPENED' in output:
                print '>>EVENT HAPPENED'

            if self.jscon.stat_mode:
                self.jscon.stat['stat'], self.jscon.stat['runtime'] = self.jscon.filter_stat_out(output, True)


            """
            ans = raw_input('continue? (y/n)')
            if ans == 'n':
                return False
                
            import time
            time.sleep(10)
            """



        return True

    def add_proposal(self, func, proposals):
        config = self.get_fuzz_config()
        if config not in self.config_list:
            proposals.append( {'id':len(proposals), 'function_name': func.function_name
                                  , 'fuid': func.cfg.fuid.split('|')[1], 'cfg': config} )
            self.config_list.append(config)


    def generate_proposals(self, fuzz_mode = 'disable', fuzz_strategy = 1):
        if fuzz_mode == 'disable':
            fuzz_mode = 1
        elif fuzz_mode == 'repeat':
            fuzz_mode = 3
        elif fuzz_mode == 'switch_only':
            fuzz_mode = 4
        else:
            return False

        proposals = []
        self.config_list = []

        for i in range(len(self.fuzz_funclist)):
            ret = self.set_func_callpoint(i)
            if not ret:
                continue

            func = self.get_cur_func()
            sbb = self.get_cur_sbb()
            cfg = func.cfg
            cds = cfg.get_cd(sbb['id'])

            if func.counter_call > 100:
                continue

            # disable/repeat function call
            if fuzz_mode != 4:
                self.fuzz_mode = fuzz_mode
                self.branch = 0
                self.optional = 0

                self.add_proposal(func, proposals)

            if fuzz_strategy == 0:
                continue

            for cd_sbb_id in cds:
                cd_sbb_index = cfg.get_sbb_index(cd_sbb_id)
                cd_sbb = cfg.sbbs[cd_sbb_index]

                # ignore if this is try-catch
                if cd_sbb['control'] in ['6','7']:
                    #pass
                    continue

                # get branch index
                branch_indx = cfg.get_connected_edge(cd_sbb_id, sbb['id'])
                if branch_indx is None:
                    print 'Failed getting connected branch index between ', cd_sbb_id, sbb['id']
                    continue

                self.sbb_index = cd_sbb_index
                self.stmt_index = len(cd_sbb['statements']) - 1 # the last statement

                # first, disable/repeat block
                if True and fuzz_mode != 4:
                    self.fuzz_mode = fuzz_mode
                    self.branch = branch_indx
                    self.optional = 0

                    self.add_proposal(func, proposals)

                if fuzz_mode == 3: #repeat
                    continue
                # then, switching
                for indx, branch_id in enumerate(cfg.graph[cd_sbb_id]):
                    if indx == branch_indx:
                        continue

                    self.fuzz_mode = 2
                    self.branch = indx
                    self.optional = 0

                    self.add_proposal(func, proposals)

        return proposals














