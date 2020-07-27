from jsflowtamper import JsFlowTamper

# tampering test options
options = {
    'chrome_path': '/Users/yirugi/workspace/research/new_chromium/chromium/src/out/Release/Chromium.app/Contents/MacOS/Chromium',
    'working_dir': './test_workingdir/etonline',
    'domain': 'etonline.com',
    'init_session_script': None,
    'test_script': 'test.js',
    'page_timeout': 15,
    'target_dom_selector': '.player__container--ad-blocking-message',
    'adblock': True,
    'init_session_before_batch': False,
    'enable_event_based_screening': False,
    'enable_widevine': False,
    'always_reset_chrome_cache': True,
}

jft = JsFlowTamper(options=options)
jft.run_collect_dynamic_data()
jft.run_tampering(batch_cnt=10, start_indx=0)

# run browser without any mods
# jft.run_clean()

# to confirm test result again
# jft.run_tampering_check(test_id=202)

