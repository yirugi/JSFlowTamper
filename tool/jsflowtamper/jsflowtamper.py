from jsconfuzzer import JsConFuzzer
import os, shutil

JS_TEMPLATE = """
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

exports.test = async function(pb, dumpio, devtool, test_output){
    pb.load_adblock = %s;
    
    let usrdir = '%s';
    if(usrdir)
        await pb.start_browser(dumpio, devtool, true, true, ['--user-data-dir=' + usrdir]);
    else
        await pb.start_browser(dumpio, devtool, true, true);
    if(pb.load_adblock)
        await sleep(2000);    
    
    let widevine = %s;
    if(widevine)
        await pb.enableWideVine();
    
    await pb.page.bringToFront();
    await pb.addDOMMonitor('%s');
    
    pb.saveResult(test_output, %s);
    
    let page = pb.page;
    
    // test script start
    %s
"""

class JsFlowTamper:
    def __init__(self, options):
        options['working_dir'] = os.path.abspath(options['working_dir'])
        options['chrome_path'] = os.path.abspath(options['chrome_path'])
        if 'enable_widevine' in options and options['enable_widevine']:
            options['page_timeout'] += 3


        self.option = options
        self.TMP_PATH = options['working_dir'] + '/tmp_data/'

        if not os.path.exists(self.TMP_PATH):
            os.makedirs(self.TMP_PATH)

    def create_test_script(self, test_script_filename, add_close=False):
        adblock = 'false'
        if 'adblock' in self.option and  self.option['adblock']:
            adblock = 'true'

        widevine = 'false'
        if 'enable_widevine' in self.option and self.option['enable_widevine']:
            widevine = 'true'


        with open(self.option['working_dir'] + '/' + test_script_filename, 'r') as f:
            test_js = f.read()

        chrome_tmp_dir = self.TMP_PATH + 'chromium_tmp'
        if 'always_reset_chrome_cache' in self.option and self.option['always_reset_chrome_cache']:
            chrome_tmp_dir = 'null'

        js = JS_TEMPLATE % (adblock, chrome_tmp_dir , widevine, self.option['target_dom_selector']
                            , (self.option['page_timeout'] - 4)* 1000, test_js)

        if add_close:
            js += "\npb.close();"

        js += '\n}'

        with open(self.TMP_PATH + test_script_filename, 'w') as f:
            f.write(js)


    def run_init_session_script(self):
        if os.path.exists(self.TMP_PATH + 'chromium_tmp'):
            shutil.rmtree(self.TMP_PATH + 'chromium_tmp')

        if 'init_session_script' not in self.option or self.option['init_session_script'] is None:
            return


        self.create_test_script(self.option['init_session_script'], add_close=True)
        jscon = JsConFuzzer(self.TMP_PATH + self.option['init_session_script'], self.option['working_dir']
                            , self.option['chrome_path'], rename_dyn=False)
        jscon.run_clean()

    def run_collect_dynamic_data(self):
        self.run_init_session_script()

        self.create_test_script(self.option['test_script'])
        jscon = JsConFuzzer(self.TMP_PATH + self.option['test_script'], self.option['working_dir']
                            , self.option['chrome_path'], domain=self.option['domain'])

        # jscon.load_from_file()
        jscon.run_get_callstack(timeout=self.option['page_timeout'] + 5)
        jscon.run_get_trace(timeout=self.option['page_timeout'])
        jscon.print_confuzz_trials(True)

    def run_tampering(self, batch_cnt=10, start_indx=0):
        jscon = JsConFuzzer(self.TMP_PATH + self.option['test_script'], self.option['working_dir']
                            , self.option['chrome_path'], domain=self.option['domain'])
        self.create_test_script(self.option['test_script'])
        jscon.load_from_file()
        jft = None
        if 'init_session_before_batch' in self.option and self.option['init_session_before_batch']:
            jft = self
        jscon.run_confuzz(batch_cnt, start_indx, timeout=self.option['page_timeout']+5
                          , kill_if_event=self.option['enable_event_based_screening'], jft=jft)

    def run_clean(self):
        # self.run_init_session_script()
        self.create_test_script(self.option['test_script'])
        jscon = JsConFuzzer(self.TMP_PATH + self.option['test_script'], self.option['working_dir']
                            , self.option['chrome_path'], domain=self.option['domain'])
        
        jscon.run_clean()

    def run_tampering_check(self, test_id):
        jscon = JsConFuzzer(self.TMP_PATH + self.option['test_script'], self.option['working_dir']
                            , self.option['chrome_path'], domain=self.option['domain'])

        jscon.load_from_file()
        jft = None
        if 'init_session_before_batch' in self.option and  self.option['init_session_before_batch']:
            jft = self
        jscon.run_tampering_check(int(test_id), jft=jft)



