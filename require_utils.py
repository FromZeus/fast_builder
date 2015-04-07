import itertools
import sys
from distutils.version import LooseVersion
import re


class Require:

    packageName = re.compile("[a-zA-Z0-9-_.]+")
    packageEq = re.compile("(>=|<=|>|<|==|!=)+")
    packageVers = re.compile("[\d.]+")
    alpha = re.compile("[a-zA-Z]")

    epochRe = re.compile("[(]\d[:]")

    packs = dict()

    def __init__(self, req):
        self.packs = req
        for el in self.packs.keys():
            self.packs[el] = sorted(self.packs[el], key = lambda x: LooseVersion(x[1]))

    # "merge" function is for merging requirements. It is processing list of requirements
    # and returns combined list of requirements in particular way.
    # Example of output: { "pbr" : [("!=", "0.7"), (">=", "0.6"), ("<", "1.0")] }
    @staticmethod
    def merge(req1, req2):
        req = dict(req1.items() + req2.items())

        for el in req1.keys():
            # Merge requirements sets
            req[el] = set(req[el]) | set(req1[el])
            # Sort requirements list by the version
            req[el] = sorted(req[el], key = lambda x: LooseVersion(x[1]))

            try:
                eqEl = filter(lambda x: x[0] == '==', req[el])[-1]
            except IndexError:
                eqEl = ("0", "0")

            try:
                neqEl = filter(lambda x: x[0] in ['>=', '<=', '>', '<'], req[el])[-1]
            except IndexError:
                neqEl = ("0", "0")

            # If equal's version is greater than '>=' or '<=', then take '=='
            # as main requirement's version of the package. Else we have to process merged list.
            if LooseVersion(eqEl[1]) >= LooseVersion(neqEl[1]):
                eqEly = True
                if eqEl[1] == neqEl[1] == "0":
                    eqEl = []
            else:
                eqEly = False

            # Processing of two lists of requirements merged in one
            # (deleting duplicates of versions with resolving conflicts).
            if not eqEly:
                pred = None
                idx = 0
                while idx < len(req[el]):
                    if pred != None:
                        if req[el][idx][1] == pred[1]:
                            if req[el][idx][0] in ['!=', '==']:
                                req[el][idx], req[el][idx - 1] = req[el][idx - 1], req[el][idx]
                            if req[el][idx][0] in ['>', '<']:
                                req[el].pop(idx - 1)
                            elif req[el][idx][0] in ['>=', '<=']:
                                if not req[el][idx - 1][0] in ['!=', '<=', '>=']:
                                    req[el].pop(idx - 1)
                                elif req[el][idx - 1][0] == '!=':
                                    req[el][idx] = (req[el][idx][0][:1], req[el][idx][1])
                                    req[el].pop(idx - 1)
                                else:
                                    idx += 1
                            idx -= 1
                    pred = req[el][idx]
                    idx += 1

                # Filter out '!=' signs.
                res = filter(lambda x: x[0] == '!=', req[el])
                for i in reversed(req[el]):
                    if i[0] in ['>', '>=']:  # Take first '>' or '>=' sign from the end.
                        res.append(i)
                        break
                for i in req[el]:
                    if i[0] in ['<', '<=']:  # Take first '<' or '<=' from the begin.
                        res.append(i)
                        break
                req[el] = res
            else:
                req[el] = []
                if eqEl:
                    req[el].append(eqEl)

        return req

    # This function is for parsing requirements file to special format:
    # [(sign, version),..., (sign, version)].
    # Output example: { "pbr" : [ (">=", "0.6"), ("!=", "0.7"), ("<", "1.0")] }
    @staticmethod
    def parse_req(inp):
        res = dict()
        for line in inp:
            if line == '' or line[0] == '#':
                continue
            resName = Require.packageName.search(line)
            resEq = Require.packageEq.findall(line)
            it = next(re.finditer('>=|<=|>|<|==|!=', line), None)
            if it:
                resVers = Require.packageVers.findall(line[it.start():])
            if resName:
                name = resName.group(0)
                if not res.has_key(name):
                    res[name] = set()
                    for idx, sign in enumerate(resEq):
                        res[name].add((sign, resVers[idx]))
        return res

    # This function is for getting package names from control file
    @staticmethod
    def get_packs_control(inp):
        sections = ["Build-Depends-Indep:", "Build-Depends:", "Depends:"]
        res = dict((el, set()) for el in sections)
        sectEnable = ""
        for line in inp:
            if line == '' or line[0] == '#':
                continue
            if sectEnable and not ',' in line:
                sectEnable = ""
            for sect in sections:
                if sect in line:
                    sectEnable = sect
                    break
            if sectEnable:
                match = Require.packageName.findall(line)
                for el in match:
                    if Require.alpha.search(el) and not el + ":" in sections:
                        res[sectEnable].add(el)
        return res

    # This function is for getting package names from spec file
    @staticmethod
    def get_packs_spec(inp):
        sections = ["BuildRequires:", "Requires:"]
        res = dict((el, set()) for el in sections)
        for line in inp:
            sectEnable = ""
            if line == '' or line[0] == '#' or '%' in line:
                continue
            for sect in sections:
                if sect in line:
                    sectEnable = sect
                    break
            if sectEnable:
                match = Require.packageName.findall(line)
                for el in match:
                    if Require.alpha.search(el) and not el + ":" in sections:
                        res[sectEnable].add(el)
        return res

    # Checks every line single in every single repository for epoch
    @staticmethod
    def get_epoch(inp):
        for line in inp:
            if "Epoch" in line or Require.epochRe.search(line):
                return line
        return None

    # Check if requirements lists have beend changed by detecting if they are different
    @staticmethod
    def is_changed(req_list1, req_list2):
        try:
            signList_a, verList_a = zip(*req_list1)
        except ValueError:
            signList_a, verList_a = '', ''
        try:
            signList_b, verList_b = zip(*req_list2)
        except ValueError:
            signList_b, verList_b = '', ''
        if set(signList_a) != set(signList_b) or set(verList_a) != set(verList_b):
            return True
        else:
            return False

    # Get N-gramm of word. It is necessary for fuzzy search
    @staticmethod
    def get_Ngramms(line, n):
        res = list()
        for i in xrange(len(line)):
            if i > n - 1:
                res.append(line[(i - n):(i + n)])
        return res

    # Correlate package with packages in requirements dictionary
    @staticmethod
    def correlate(req_dict, pack_name):
        _pack_name = pack_name
        if "python-" in _pack_name:
            idx = _pack_name.index("python-")
            _pack_name = _pack_name[idx + len("python-"):len(_pack_name)]
        if _pack_name in req_dict.keys():
            return _pack_name
        gr = Require.get_Ngramms(_pack_name, 2)
        count = dict((el, 0) for el in req_dict.keys())
        for key in req_dict.keys():
            for syll in gr:
                if syll in key:
                    count[key] += 1
        return max(count, key=count.get)