'use strict';

const PuppetBrowser = require('./puppet_browser.js');
const fs = require('fs');
let path = require('path');


// read arguments
if(process.argv.length < 6){
    console.log('Need parameters. ex) node run_puppet.js [chrome path] [working_dir] [testing script] [testing mode] [testing output filename]');
    process.exit(1);
}

let test_js = process.argv[4];
let mode = process.argv[5];
let test_output = null;
if(process.argv.length === 7)
    test_output = process.argv[6];

let test_module = require(test_js);

let pb = new PuppetBrowser();
pb.working_dir = process.argv[3];
pb.mod_chrome_path = process.argv[2];
pb.testing_step = parseInt(mode);

if(mode === '0') {
    test_module.test(pb, false, true, test_output);
} else if (mode === '1') {
    test_module.test(pb, true, false, test_output);
} else {
    test_module.test(pb, false, false, test_output);
}





