from jsflowtamper import JsFlowTamper

# tampering test options
options = {
    'chrome_path': '/Users/yirugi/workspace/research/new_chromium/chromium/src/out/Release/Chromium.app/Contents/MacOS/Chromium',
    'working_dir': './test_workingdir/latimes',
    'domain': 'latimes.com',
    'init_session_script': 'init.js',
    'test_script': 'test.js',
    'page_timeout': 10,
    'target_dom_selector': '#reg-overlay',
    'adblock': False,
    'init_session_before_batch': True,
    'enable_event_based_screening': False,
    'enable_widevine': False,
    'always_reset_chrome_cache': False,
}

jft = JsFlowTamper(options=options)
jft.run_collect_dynamic_data()
jft.run_tampering(batch_cnt=10, start_indx=0)

# run browser without any mods
# jft.run_clean()

# to confirm test result again
# jft.run_tampering_check(test_id=3)


