"use strict"

const puppeteer = require('puppeteer');
const fs = require('fs');
const sleep = require('sleep');
const util = require('util');

const writeFile = util.promisify(fs.writeFile);

function PuppetBrowser() {
    this.working_dir = null;
    this.mod_chrome_path = null;
    this.browser = null;
    this.page = null;
    this.dom_track = true;
    this.load_adblock = false;

    this.selector = '';
    this.timerDomTracking = null;
    this.oldHtml = null;

    this.processing = 0;
    this.testing_step = 0;

    this.enableInterceptConsole = function (intercept_all_console) {
        if (intercept_all_console) {
            this.page.on('console', msg => {
                if (msg._text.indexOf('>>PUPPET:') !== -1) {
                    console.log(msg._text);
                }

                if (msg._text.indexOf('>>RUNTIME:') !== -1)
                    console.log(msg._text);

                if (msg._text.indexOf('>>EVENT_INFO:') !== -1)
                    console.log(msg._text);

                if (msg._type === 'trace') {
                    this.printCallStack(msg._text);
                }
            });
        } else {
            this.page.on('console', msg => {
                if (msg._text.indexOf('>>PUPPET:') !== -1) {
                    console.log(msg._text);
                    if (this.testing_step === 2) {
                        if (msg._text.indexOf('EVENT HAPPENED') !== -1) {
                            setTimeout(this.close, 100);
                        }
                    }
                }
            });
        }
    };

    this.setRecentAgentHeader = async function () {
        let agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3673.0 Safari/537.36';
        await this.page.setUserAgent(agent);
    }

    this.start_browser = async function (dumpio = true, devtools = true, intercept_all_console = true, mod_chrome = true, args = []) {

        process.chdir(this.working_dir);

        args.push('--no-sandbox', '--mute-audio');
        if (this.load_adblock)
            args.push('--load-extension=' + __dirname + '/adblock/', '--disable-extensions-except=' + __dirname + '/adblock/');

        let params = {headless: false, args: args, ignoreHTTPSErrors: true, devtools: devtools, dumpio: dumpio};

        if (mod_chrome)
            params.executablePath = this.mod_chrome_path;

        this.browser = await puppeteer.launch(params);
        this.page = await this.browser.newPage();
        // this.setRecentAgentHeader();
        let page = this.page;
        this.enableInterceptConsole(intercept_all_console);
        await page.setViewport({height: 900, width: 1200});
    }

    this.load_page = async function (url, selectorForWait = null, selectorVisible = true, timeout = 300000) {
        await this.page.goto(url, {timeout: timeout});
        if (selectorForWait != null) {
            await this.page.waitForSelector(selectorForWait, {visible: selectorVisible})
        }
    }

    this.addDOMMonitor = async function (selector) {
        if (!this.dom_track)
            return;

        if (this.testing_step === 1 || this.testing_step === 3)
            return;
        // if(this.testing_step === 1 || this.testing_step === 3 || this.testing_step === 2)
        //     return;

        this.selector = selector;
        await this.page.evaluateOnNewDocument((selector, testing_step) => {

            var cb = function (ev) {
                var node = ev.target;
                var node_doc = node.ownerDocument;
                if (node_doc == null)
                    node_doc = document;
                var targetDom = node_doc.querySelector(selector);
                //if(targetDom != null && (node.contains(targetDom) || targetDom === node)){
                //if(targetDom != null && targetDom === node){
                if (targetDom != null && (node.contains(targetDom) || targetDom.contains(node) || targetDom === node)) {
                    if (testing_step === 0) {
                        console.trace();
                    } else if (testing_step === 2) {
                        console.log('>>PUPPET:EVENT HAPPENED');
                    }

                }
            };
            //var events = ['DOMAttrModified','DOMAttributeNameChanged','DOMCharacterDataModified','DOMElementNameChanged','DOMNodeInserted','DOMNodeInsertedIntoDocument','DOMNodeRemoved','DOMNodeRemovedFromDocument','DOMSubtreeModified'];
            var events = ['DOMNodeInserted', 'DOMNodeInsertedIntoDocument', 'DOMNodeRemoved', 'DOMNodeRemovedFromDocument', 'DOMSubtreeModified'];

            //var events = ['DOMSubtreeModified']
            for (var event of events) {
                document.addEventListener(event, cb);
            }

            //console.log(document);


        }, selector, this.testing_step);
    };

    this.close = function (pb = this) {
        if (pb.processing != 0) {
            setTimeout(this.close, 2000, pb);
        } else {
            setTimeout((pb) => {
                pb.browser.close()
            }, 5000, pb);
        }
    }

    this.sleep = function(ms) {
      return new Promise(resolve => setTimeout(resolve, ms));
    }

    this.enableWideVine = async function () {
        await this.page.goto('chrome:components');
        await this.page.click('#oimompecagnajdejgnnjijobebaeigek');
        await this.sleep(3000);
    }

    this.printCallStack = function (data) {
        this.processing += 1;
        data = JSON.parse(data);
        let stack = {};
        let anon_indx = 0;

        let dataitem = data;
        let json_str = "[";
        let first_one = true;

        let noname_scripts = {};

        while (true) {
            let frames = dataitem.callFrames;

            for (let i = 0; i < frames.length; i++) {
                if (first_one) {
                    first_one = false;
                    continue;
                }
                let stack_item = frames[i];
                let pos = (stack_item.lineNumber + 1) + ":" + (stack_item.columnNumber + 1);
                let source_url = stack_item.url;
                let scriptId = stack_item.scriptId;

                if (source_url.substr(0, 4) !== 'http') {
                    if (source_url !== "")
                        noname_scripts[scriptId] = source_url;
                }

                if (stack.hasOwnProperty(source_url)) {
                    stack[source_url].push(pos);
                } else {
                    stack[source_url] = [pos];
                }
                let fname = stack_item.functionName === "" ? "(anonymous)" : stack_item.functionName;
                console.debug(fname + ' at (' + pos + ') ' + source_url);
                json_str += '{"function_name":"' + fname + '", "position":"' + pos + '", "source_url":"' + source_url + '"}';
                if (i + 1 < frames.length)
                    json_str += ',';
            }

            if (!dataitem.hasOwnProperty('parent'))
                break;
            dataitem = dataitem.parent;
            if (json_str.substr(json_str.length - 1) !== ',')
                json_str += ',';
        }

        if (json_str.substr(json_str.length - 1) === ',')
            json_str = json_str.substr(0, json_str.length - 1);
        json_str += ']';
        console.log(json_str);

        // download noname script
        (async () => {
            await this.page._client.send('Debugger.enable');
            for (let script_id in noname_scripts) {
                let res = await this.page._client.send('Debugger.getScriptSource', {'scriptId': script_id});
                writeFile(this.working_dir + 'tempjs/' + noname_scripts[script_id], res.scriptSource);
            }
            this.processing -= 1;
        })();
    }
    

    this.saveResult = async function (test_output, time) {
        if (test_output !== null) {
            setTimeout(async () => {
                let base_path = this.working_dir;
                let opt = {path: base_path + 'screenshot/' + test_output + '.jpg', type: 'jpeg', quality: 50};
                await this.page.screenshot(opt);

                let src = await this.page.content();
                fs.writeFile(base_path + 'html/' + test_output + '.html', src, function (err) {
                    if (err) {
                        return console.log(err);
                    }
                });

            }, time);
        }
    }
}

module.exports = PuppetBrowser;