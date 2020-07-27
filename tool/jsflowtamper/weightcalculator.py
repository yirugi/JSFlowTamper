from difflib import SequenceMatcher
from urlparse import urlparse
import numpy as np
from sklearn.preprocessing import StandardScaler
import pickle, os

class WeightCalculator:
    def __init__(self, csi, domain):
        self.csi = csi
        self.domain = domain


    def scaleFeatures(self, data):
        scaler = StandardScaler()
        scaler.fit(data)
        return scaler.transform(data)


    def getFeatureData(self, func_list):
        # domain similarity
        domsim_list = self.cal_domainsim(func_list)

        # position in a callstack
        pos_list = self.cal_pos(func_list)

        # function called count
        func_called_list = self.cal_func_called(func_list)

        # callstack indx
        csindx_list = self.cal_cs_indx(func_list)

        # function entered count
        func_entered_list = self.cal_func_entered(func_list)

        features = list()
        features.append(domsim_list)
        features.append(pos_list)
        features.append(func_called_list)
        features.append(csindx_list)
        features.append(func_entered_list)

        # scaling
        npFeatures = np.array(features)
        npFeatures = np.transpose(npFeatures)

        return self.scaleFeatures(npFeatures)

    def getWeights(self, scaledFeatures):
        this_dir, this_filename = os.path.split(__file__)
        clf = pickle.load(open(this_dir + '/brf.model', 'rb'))
        Y_pred = clf.predict_proba(scaledFeatures)
        # ranks = [i[0] for i in sorted(enumerate(Y_pred[:, 1]), key=lambda x: x[1], reverse=True)]

        # return
        return Y_pred[:, 1]


    def calculate(self, print_result = False):
        # delete funcs not having cfg
        func_list = list()
        for func in self.csi.func_list:
            if func.cfg is not None:
                func_list.append(func)

        scaledFeatures = self.getFeatureData(func_list)
        weights = self.getWeights(scaledFeatures)

        for i, func in enumerate(func_list):
            func.weight = weights[i]

        # sort by weight
        sorted_list = sorted(func_list, key=lambda x: x.weight, reverse=True)
        self.csi.sorted_func_list = sorted_list

        """
        for func in sorted_list:
            print func.weight
        """

    def getFeatures(self):
        """
        func_list = list()
        for func in self.csi.func_list:
            if func.cfg is not None:
                func_list.append(func)
        """
        func_list = self.csi.sorted_func_list

        # domain similarity
        domsim_list = self.cal_domainsim(func_list)

        # function appearance in other callstack
        func_appr_list = self.cal_func_appr(func_list)

        # position in a callstack
        pos_list = self.cal_pos(func_list)

        # function called count
        func_called_list = self.cal_func_called(func_list)

        # callstack indx
        csindx_list = self.cal_cs_indx(func_list)

        # callstack length
        cslen_list = self.cal_cs_length(func_list)

        # function entered count
        func_entered_list = self.cal_func_entered(func_list)

        # branch cnt in a function
        branch_cnt_list = self.cal_branch_cnt(func_list)

        # dom access
        dom_access_list = self.cal_dom_access(func_list)

        # js load index
        js_load_indx_list = self.cal_js_indx(func_list)

        features = list()
        features.append(domsim_list)
        features.append(func_appr_list)
        features.append(pos_list)
        features.append(func_called_list)
        features.append(csindx_list)
        features.append(cslen_list)
        features.append(func_entered_list)
        features.append(branch_cnt_list)
        features.append(dom_access_list)
        features.append(js_load_indx_list)

        output = 'id,func_name,f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,class\n'
        for i, func in enumerate(func_list):
            output += str(i) + ',' + func.function_name
            for feature in features:
                output += ',' + str(feature[i])
            output += ',0\n'

        print output





    def _calculate(self, print_result = False):
        #self.getFeatures()
        #print_result = False

        # delete funcs not having cfg
        func_list = list()
        for func in self.csi.func_list:
            if func.cfg is not None:
                func_list.append(func)


        # calculate weight
        # domain similarity
        domsim_list = self.cal_domainsim(func_list)


        # function appearance in other callstack
        func_appr_list = self.cal_func_appr(func_list)

        # position in a callstack
        pos_list = self.cal_pos(func_list)

        # function called count
        func_called_list = self.cal_func_called(func_list)

        # callstack indx
        csindx_list = self.cal_cs_indx(func_list)



        dom_access_list = self.cal_dom_access(func_list)


        features = list()
        features.append(domsim_list)
        # features.append(self.feature_scaling(func_appr_list))
        features.append(self.feature_scaling(pos_list, inverse=True))
        features.append(self.feature_scaling(func_called_list, inverse=True, zero_to_max=True))
        features.append(self.feature_scaling(csindx_list, inverse=True))
        # features.append(self.feature_scaling(dom_access_list, inverse=True))

        # f_sensitivity = [1,0.3,1,10, 1]
        f_sensitivity = [1, 1, 10, 1]

        for i, func in enumerate(func_list):
            f_sum = 0
            for j, f in enumerate(features):
                f_sum = f_sum + (f[i] * f_sensitivity[j])
            func.weight = f_sum


        if print_result:
            for i, func in enumerate(func_list):
                print str(i+1) + ',',
                print func.function_name + ',',
                print ','.join([str(f[i]) for f in features]),',',
                print func.weight


        # sort by weight
        sorted_list = sorted(func_list, key=lambda x: x.weight, reverse=True)

        self.csi.sorted_func_list = sorted_list

        """
        for func in sorted_list:
            print func.weight
        """

    def cal_domainsim(self, func_list):
        def similar(a, b):
            return SequenceMatcher(None, a, b).ratio()

        def get_baseurl(url):
            return urlparse(url).netloc

        domain = self.domain
        if domain[0:4] == 'www.':
            domain = domain[4:]

        #domain = get_baseurl(domain)


        domsim_list = []
        domsim_store = {}
        for func in func_list:
            s_url = get_baseurl(func.source_url)
            if s_url in domsim_store:
                domsim = domsim_store[s_url]
            else:
                if domain in s_url:
                    domsim = 1
                else:
                    domsim = similar(domain, s_url)

                #print func.source_url, domsim
                domsim_store[s_url] = domsim

            domsim_list.append(domsim)

        return domsim_list


    def cal_func_appr(self, func_list):

        if len(self.csi.cs_list) == 1:
            return [0] * len(func_list)

        func_appr_list = []

        for func in func_list:
            appear_cnt = 0
            if func.cfg is not None:
                fuid = func.cfg.fuid

                for i, cs in enumerate(self.csi.cs_list):
                    if i == func.cs_indx:
                        continue

                    for f in cs:
                        if f.cfg is not None and fuid == f.cfg.fuid:
                            appear_cnt += 1
                            break

            func_appr_list.append(appear_cnt)
            #print func.function_name, appear_cnt


        #func_appr_list = self.feature_scaling(func_appr_list)

        return func_appr_list

    def cal_pos(self, func_list):
        pos_list = []
        for func in func_list:
            cs = self.csi.cs_list[func.cs_indx]
            f_indx = cs.index(func)
            #f_cnt = len(cs)

            pos_list.append(f_indx)
            #print func.function_name, f_indx

        return pos_list


    def cal_func_called(self, func_list):
        func_called_list = []
        for func in func_list:
            func_called_list.append(func.counter_call)
            #print func.function_name, func.counter_call

        return func_called_list

    def cal_cs_indx(self, func_list):
        csindx_list = [func.cs_indx for func in func_list]

        return csindx_list

    def feature_scaling(self, data, inverse=False, zero_to_max = False):
        if len(data) == 0:
            return []
        x_min = min(data)
        x_max = max(data)
        v = float(x_max - x_min)
        if v==0:
            return [0] * len(data)

        if zero_to_max:
            data = [x_max if x==0 else x for x in data]

        if inverse:
            data = [1 - ((x - x_min) / v) for x in data]
        else:
            data = [((x - x_min) / v) for x in data]

        return data

    def cal_cs_length(self, func_list):
        cs_cnt_list = []
        for func in func_list:
            cs = self.csi.cs_list[func.cs_indx]
            cs_cnt_list.append(len(cs))

        return cs_cnt_list


    def cal_func_entered(self, func_list):
        func_entered_list = []
        for func in func_list:
            func_entered_list.append(func.counter_entered)
            #print func.function_name, func.counter_call

        return func_entered_list

    def cal_branch_cnt(self, func_list):
        branch_cnt_list = []


        for func in func_list:
            branch_cnt = 0
            for sbb in func.cfg.sbbs:
                for st in sbb['statements']:
                    if st['node_type'] in ['8', '12', '34']:
                        branch_cnt += 1

            branch_cnt_list.append(branch_cnt)

        return branch_cnt_list

    def cal_dom_access(self, func_list):
        JS_DOM_ACC_FUNC = ['appendChild','removeChild','insertBefore','replaceChild']
        # jquery ['append','prepend','after','before']

        dom_access_list = []

        for func in func_list:
            dom_access = 0
            #print func.call_fname, func.call_fname in JS_DOM_ACC_FUNC
            if func.call_fname in JS_DOM_ACC_FUNC:
                dom_access = 1

            dom_access_list.append(dom_access)

        return dom_access_list

    def cal_js_indx(self, func_list):
        return [func.script_indx for func in func_list]





















