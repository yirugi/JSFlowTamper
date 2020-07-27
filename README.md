# JSFlowTamper

This repository contains the implementation of the paper [Finding Business Flow Tampering Vulnerability](https://yirugi.github.io/papers/icse2020_jsflow.pdf) published in ICSE 2020. 

## Abstract

The sheer complexity of web applications leaves open a large attack surface of business logic. Particularly, in some scenarios, developers
have to expose a portion of the logic to the client-side in order to coordinate multiple parties (e.g. merchants, client users, and thirdparty payment services) involved in a business process. However, such client-side code can be tampered with on the fly, leading to business logic perturbations and financial loss. Although developers become familiar with concepts that the client should never be trusted, given the size and the complexity of the client-side code that
may be even incorporated from third parties, it is extremely challenging to understand and pinpoint the vulnerability. To this end, we investigate client-side business flow tampering vulnerabilities and develop a dynamic analysis based approach to automatically identifying such vulnerabilities. We evaluate our technique on 200 popular real-world websites. With negligible overhead, we have successfully identified 27 unique vulnerabilities on 23 websites, such as New York Times, HBO, and YouTube, where an adversary can interrupt business logic to bypass paywalls, disable adblocker detection, earn reward points illicitly, etc.

## Reference

I Luk Kim, Yunhui Zheng, Hogun Park, Weihang Wang, Wei You, Yousra Aafer, Xiangyu Zhang, "Finding Client-side Business Flow Tampering Vulnerabilities", The 42nd International Conference on Software Engineering (ICSE), 2020


## Installation
### Build Chromium with modified V8 engine
+ IMPORTANT! Please use python 2 for build.

#### Basic Chromium build instruction
Please refer the basic instructions in the following links:
[Mac](https://chromium.googlesource.com/chromium/src/+/master/docs/mac_build_instructions.md)
[Linux](https://chromium.googlesource.com/chromium/src/+/master/docs/linux/build_instructions.md)

#### Change to the specific version of Chromium code
After getting the code by `fetch chromium` command, you need to change the current Chromium code to the specific version that we used for the implementation.

Go to `src` directory. Then, run the following command:

```
src $ git checkout 089264e2846ad03c699a922e4849accd399fa279
src $ cd ..
    $ gclient sync -D --force --reset
```

If you encounter any issues, please try to get old version of `depot_tools` as well as indicated [here](https://chromium.googlesource.com/chromium/src.git/+/master/docs/building_old_revisions.md)

#### Overwrite modified files
Copy `install/mod_files.zip` to `src` directory. Then run the following command:

`src $ unzip -o ./mod_files.zip`

#### Widevine support
Create a directory:

+ For Linux:

`src $ mkdir -p third_party/widevine/cdm/linux/x64`

+ For Mac

`src $ mkdir -p third_party/widevine/cdm/mac/x64`

Copy the file `install/widevine_cdm_version.h` to the location.

#### Build Chromium
You can continue to build by following the basic instruction.


### Install python modules
Install the following modules. Again, please use Python 2. The versions we used are included.
```
cloudpickle			1.3.0
graphviz			0.14
html-similarity			0.3.2
imbalanced-learn		0.4.3
networkx			2.2
numpy				1.16.6
opencv-python			4.2.0.32	
parsel				1.2.0
psutil				5.7.0
requests			2.23.0
scikit-image			0.14.5
scikit-learn			0.20.4
scipy				1.2.3
subprocess32			3.5.4
urllib3				1.25.9
```

## JSFlowTamper Usage
+ There are 4 example files in `/tool/` directory. You can find basic usages by checking those examples.

### Create initial and test JavaScript files

+ We decided not to include the extension that records a user's interactions with a browser generating browsing automation script, and DOM selectors as in Sec. 4.1. This is because our prototype extension might not work properly on every case and platform. Instead, you can use this existing extension [Puppeteer Recorder](https://chrome.google.com/webstore/detail/puppeteer-recorder/djeegiggegleadkkbgopoonhjimgehda). You can also fabricate your own script. You can find some examples [here](https://github.com/puppeteer/puppeteer).

The first thing is you need to decide if you want to use 'initial' script. An 'initial' script can be used to create sessions for testing. For example, in order to test paywall system, you may want to read some number of articles to trigger the paywall message. Here is an example of the 'initial' script for testing LATimes paywall system. 

```javascript
/* please remove these lines if you use Puppeteer Recorder extension.
const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch()
  const page = await browser.newPage()
*/
const navigationPromise = page.waitForNavigation()

await page.goto('https://www.latimes.com/')

await page.setViewport({ width: 1274, height: 860 })

await navigationPromise

await page.waitForSelector('.list-items-item:nth-child(2) > .promo-medium > .promo-wrapper > .promo-content > .promo-title-container > .promo-title > .link')
await page.click('.list-items-item:nth-child(2) > .promo-medium > .promo-wrapper > .promo-content > .promo-title-container > .promo-title > .link')

await navigationPromise

await navigationPromise

/* also, remove these lines
await browser.close()
})()
*/
```

This code is originally generated by the Puppeteer Recorder extension. Note that you need to remove some lines as indicated.

After creating the initial script, now you should create a test script. In the paywall case, this can be visiting an article page. Here is an example of the test script for LATimes case.

```javascript
await page.goto('https://www.latimes.com/california/story/2020-07-19/baristas-lose-jobs-covid-19-unionization-augies-coffee-house')
````

Lastly, create any working directory, then put those files there.

### Get a selector of business-related DOM object

As we indicated in the paper, you need a selector of business-related DOM object in order to collect callstack trace. For example, a paywall message box can be the DOM object we want to observe. For a video advertisement case, you can use any DOM objects, such as a text message box or an image containing ads. For the LATimes case, we use the following selector:

`#reg-overlay`

### Create a python script for tampering testing

Now, you can create a tampering testing script. The script should be located at the same directory with other examples files (`/jsflowtamper/[test_script].py`). Let's see the testing script for LATimes case (`/jsflowtamper/test_latimes.py`).

```python
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
```

#### Tampering test options
By using the `options` variable, you can specify configurations of your tampering test.

| parameter | description |
| --------- | ----------- |
|`chrome_path`| The chromium executable path you just built.|
|`working_dir` | The working directory your initial and test scripts are located. Temp files and testing resutls will be also stored here. |
|`domain` | Main URL of the testing website. |
|`init_session_script` | Filename of an initial script |
|`test_script` | Filename of a test script |
|`page_timeout` | Timeout for testing in seconds. After x seconds, the Chromium browser is automatically terminated. |
|`target_dom_selector` | The selector of business-related DOM object |
|`adblock` | `True` if you want to use an adblock extension for testing |
|`init_session_before_batch` | `True` if you want to run the initial script to create a session before each testing batch |
|`enable_event_based_screening` | `True` if you want to use the 'Event-based screening' feature |
|`enable_widevine` | `True` if you want to enable widevine component. If some video player does not work correctly, you can solve the issue by enabling this option. |
|`always_reset_chrome_cache` | `True` if you want to reset the chromium's cache directory including session |


#### Testing APIs

##### run_collect_dynamic_data()

This function performs the dynamic data collection process. The collected data is stored at `working_dir`, and can be loaded for other functions. This means that you do not need to run this function if you run it once.


##### run_tampering(batch_cnt, start_indx)
+ `batch_cnt` The number of tampering testing for one batch. After one batch, test results are collected and clustered.
+ `start_indx` A numeric id of a tampering proposal to start testing. You can resume testing by specifying the id of a tampering proposal.

Before testing a tampering proposal, our tool shows information about the proposal. Here is an example:

```
ID: 9,
Tampering Setting: 
    <Offset: 333780,
     Branch Indx: 1,
     Tampering Mode: FORCED EXEC., 
     Opt.: 0>,
Func. Name: (anonymous),
Func. Offset: 265751,
Source URL: https://s.ntv.io/serve/load.js
```

After finishing each batch of testing, our tool collects test results and performs clustering-based screening. After the clustering, you can check one screenshot for each cluster in `working_dir/tmp_data/screenshot` in order to confirm if the tampering succeeds.

##### run_tampering_check(test_id)
+ `test_id` A numeric id of a tamering proposal to check

You can re-check the tampering proposal by using this function.

##### run_clean()
This function runs the test script without modifying execution.


#### After testing

If you find a tampering proposal that successfully alters the original business flow, you can check the location of code to investigate the vulnerability. For example, Let's assume this is the tampering proposal:

`ID: 9, Tampering Setting: <Offset: 333780, Branch Indx: 1, Tampering Mode: FORCED EXEC., Opt.: 0>, Func. Name: (anonymous), Func. Offset: 265751, Source URL: https://s.ntv.io/serve/load.js, `

Then, go to the `load.js` file and offset `333780`. The proposal shows that it performed `Forced Execution` to the brach index `1`. If the branch is `if` statement, `0` is `false` branch and `1` is `true` branch. For `swich-case` statement, each index represents each case, and `0` is for the `default` branch.



