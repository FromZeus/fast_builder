import yaml
from os.path import join, isdir
from os import listdir
import argparse
import pdb
import lan
import require_utils
import re
import json

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config', dest='config', help='Configuration YAML')
args = parser.parse_args()

packageName = re.compile("(\d*[a-zA-Z-_.]\d*)+")
packageEq = re.compile("(>=|<=|>|<|==|!=)+")
packageVers = re.compile("(\d[.]*)+")
packageNameEnd = re.compile("[a-zA-Z0-9-_.]+$")
impTemplate = re.compile("import [a-zA-Z0-9-_.]+")
fromTemplate = re.compile("from [a-zA-Z0-9-_.]+")
sectTemplate = re.compile(":.+")
build_depends = re.compile('"[a-zA-Z0-9-_.|<|>|=|!]+"')
package_with_version = \
    re.compile("(\d*[a-zA-Z-_.]\d*)+\s*(\((\s*(>>|<<|=|>=|<=)+\s*(\d[.]*)+\s*)" \
        "(\|{1}\s*(>>|<<|=|>=|<=)+\s*(\d[.]*)+\s*){,1}\)){,1},")
package_ver_not_equal = re.compile("\(.*(<<).*\|.*(>>).*\)")

build_dep_sects_list = ["Build-Depends", "Build-Depends-Indep"]
dep_sects_list = ["Depends", "Conflicts", "Provides", "Breaks",
"Replaces", "Recommends", "Suggests"]
section_list = ["Source", "Section", "Priority", "Maintainer",
"Build-Depends", "Build-Depends-Indep", "Standards-Version",
"Homepage", "Package", "Architecture", "Depends", "Description"]
main_section_list = ["Source", "Section", "Priority", "Maintainer",
"Build-Depends", "Build-Depends-Indep", "Standards-Version", "Homepage"]
package_section_list = ["Architecture", "Section", "Depends", "Conflicts",
"Provides", "Breaks", "Replaces", "Recommends", "Suggests", "Description"]
section_dict = dict()

def main():
    #pdb.set_trace()
    try:
        conf = open(args.config, 'r')
        tempConf = yaml.load_all(conf)

        for line in tempConf:
            depends = dict()
            build_depends = dict()

            launchpad_id = line["Login"]
            launchpad_pw = line["Password"]
            global_branch = line["Branch"]

            if global_branch == 'master':
                global_branch = 'master'
            elif global_branch == 'juno':
                global_branch = 'stable/juno'
            elif global_branch == 'icehouse':
                global_branch = 'stable/icehouse'
            gerritAccount = lan.login_to_launchpad(launchpad_id, launchpad_pw)

            req_url = 'https://raw.githubusercontent.com/openstack/requirements/' \
            '{0}/global-requirements.txt'.format(global_branch)
            global_req = require_utils.Require.parse_req(
                lan.get_requirements_from_url(req_url, gerritAccount))

            section_dict["Source"] = line["Source"]
            section_dict["Section"] = line["Section"]
            section_dict["Priority"] = line["Priority"]
            section_dict["Maintainer"] = line["Maintainer"]
            section_dict["Build-Depends"] = line["Build-Depends"]

            if section_dict["Build-Depends"]:
                packages_processing(section_dict["Build-Depends"])

            section_dict["Build-Depends-Indep"] = line["Build-Depends-Indep"]
            if section_dict["Build-Depends-Indep"]:
                packages_processing(section_dict["Build-Depends-Indep"])

            section_dict["Standards-Version"] = line["Standards-Version"]
            section_dict["Homepage"] = line["Homepage"]
            section_dict["Package"] = line["Package"]

            path_to_debian_dir = recur_search("debian")
            if len(section_dict["Package"]) > 1:
                for pack_name, pack_val in section_dict["Package"].iteritems():
                    if pack_val["Files"]:
                        with open(join(path_to_debian_dir, "{0}.install".format(pack_name)), "w+") as pack_install:
                            pack_install.writelines(re.sub(";\s+", "\n", pack_val["Files"]))

            for el in section_dict["Package"].keys():
                for dep_sect in dep_sects_list:
                    if section_dict["Package"][el][dep_sect]:
                        packages_processing(section_dict["Package"][el][dep_sect])
                section_dict["Package"][el]["Depends"] = \
                    get_dependencies(global_req, section_dict["Package"][el]["Depends"])

            #if len(section_dict["Package"]) == 1:

            #else:
            #   for el in section_dict["Package"].keys():


            build_system = line["Buildsystem"]
            build_with = line["BuildWith"]

            load_control()

            section_dict["Build-Depends"] = get_build_dependencies(global_req,
               section_dict["Build-Depends"])
            
            generate_control()
            generate_rules(build_system, build_with)
        conf.close()

    except KeyboardInterrupt:
        print '\nThe process was interrupted by the user'
        raise SystemExit

def packages_processing(section):
    for el in section.keys():
        section[el] = {(el1.items()[0]) for el1 in section[el]}

def get_build_dependencies(global_req, build_depends, py_file_names = ["setup.py"], update = True):
    if not build_depends:
        build_depends = dict()

    control_base_file = open("control-base.json", "r")
    base_control_file = open("base-control.json", "r")
    control_base = json.load(control_base_file)
    base_control = json.load(base_control_file)

    # Change "reuirements" style to "control" style signs and update requirements
    build_depends = dict([(base_control[key], {format_sign(el) for el in global_req[key]})
        for key, val in build_depends.iteritems()
            if check_in_base(base_control, key) and global_req.has_key(key)])

    build_depends = dict(build_depends.items() + {"python-setuptools" : {}, "python-all" : {},
        "python-dev" : {}, "debhelper" : {(">=", "9")}}.items())

    excepts = {"python-distutils.core" : {}, "python-sys" : {}, "python-setup" : {},
        "python-argparse" : {}, "python-ordereddict" : {},
        "python-multiprocessing": {}, "python-os": {}, section_dict["Source"]: {}}

    for py_file in py_file_names:
        path_to_py = recur_search(names = py_file, control_base = control_base)
        packets_from_py = load_packs(path_to_py, control_base)
        if packets_from_py:
            build_depends = dict(build_depends.items() + packets_from_py.items())

    for el in excepts:
        if build_depends.has_key(el):
            del build_depends[el]

    for el in build_depends.keys():
        if control_base.has_key(el) and global_req.has_key(control_base[el]):
            build_depends[el] = global_req[control_base[el]]

    control_base_file.close()
    base_control_file.close()

    return build_depends

def get_dependencies(global_req,
    depends,
    req_file_names = ["requires.txt", "requirements.txt"],
    update = True):
    if not depends:
        depends = dict()
    base_control_file = open("base-control.json", "r")
    base_control = json.load(base_control_file)
    
    # Change "reuirements" style to "control" style signs and update requirements
    depends = dict([(base_control[key], {format_sign(el) for el in global_req[key]})
        for key, val in depends.iteritems()
            if check_in_base(base_control, key) and global_req.has_key(key)])

    depends = dict(depends.items() + {"${shlibs:Depends}": {}, "${misc:Depends}": {}}.items())
    try:
        with open(recur_search(req_file_names), 'r') as req_file:
            for line in req_file:
                req_pack = packageName.search(line)
                if req_pack:
                    req_pack_name = req_pack.group(0)
                    if base_control.has_key(req_pack_name) and global_req.has_key(req_pack_name):
                        depends.setdefault(base_control[req_pack_name],
                            {format_sign(el1) for el1 in global_req[req_pack_name]})
            base_control_file.close()
    except (IOError, TypeError):
        print "There is no requirements!"
    return depends

def check_in_base(base, el):
    if base.has_key(el):
        return True
    else:
        return False

def format_sign(el):
    if el[0] == "<":
        return ("<<", el[1])
    elif el[0] == ">":
        return (">>", el[1])
    else:
        return el

def load_packs(path, control_base):
    try:
        with open(path, 'r') as grep_file:
            res_grep = dict()
            for line in grep_file:
                filtered_package = filter_packs(line, control_base)
                if filtered_package:
                    res_grep.setdefault(filtered_package, {})
            return res_grep
    except IOError:
        return None

def recur_search(names, relative_path = ".", search_type = "default", control_base = None):
    for el in listdir(relative_path):
        if el in names:
            return join(relative_path, el)
        elif isdir(join(relative_path, el)) and el not in ["doc"]:
            path = recur_search(names, join(relative_path, el), control_base)
            if path:
                return path
    return None

def filter_packs(line, control_base):
    req_pack = build_depends.search(line)
    imp = impTemplate.search(line)
    frm = fromTemplate.search(line)

    if req_pack:
        req_pack_name = req_pack.group(0)[1:-1:]
        try:
            res_pack_name = "python-" + re.sub("[_]", "-",
                packageName.search(req_pack_name).group(0))
        except Exception:
            return None
        res_pack_name_part = part_of_package(res_pack_name, control_base.keys())

        if len(req_pack_name) <= 1 \
            or req_pack_name.startswith('__') \
            or req_pack_name.endswith('.py') \
            or req_pack_name.endswith('.rst') \
            or not res_pack_name_part:
            if res_pack_name:
                print "Unknown package: {0}".format(res_pack_name)
            return None
        else:
            return res_pack_name_part
    elif imp or frm:
        res_pack_name_frm = res_pack_name_imp = \
        res_pack_name_frm_part = res_pack_name_imp_part = ""
        try:
            res_pack_name_frm = "python-" + re.sub("[_]", "-",
                packageNameEnd.search(frm.group(0)).group(0))
            res_pack_name_frm_part = part_of_package(res_pack_name_frm, control_base.keys())
        except Exception:
            None
        try:
            res_pack_name_imp = "python-" + re.sub("[_]", "-",
                packageNameEnd.search(imp.group(0)).group(0))
            res_pack_name_imp_part = part_of_package(res_pack_name_imp, control_base.keys())
        except Exception:
            None

        if imp and frm and res_pack_name_frm_part:
            return res_pack_name_frm_part
        elif imp and res_pack_name_imp_part:
            return res_pack_name_imp_part
        elif res_pack_name_imp and not res_pack_name_imp_part:
            print "Unknown package: {0}".format(res_pack_name_imp)
        elif res_pack_name_frm and not res_pack_name_frm_part:
            print "Unknown package: {0}".format(res_pack_name_frm_part)
    return None

def part_of_package(package, packages):
    for el in packages:
        if el in package:
            return el
    return None

def parse_packages(line, dep_flag, cur_package):
    for package_sect in package_section_list:
        if package_sect in line and package_sect != dep_flag:
            dep_flag = package_sect
            if package_sect in dep_sects_list:
                dep_flag = parse_packages(line, dep_flag, cur_package)
            else:
                section_dict["Package"][cur_package][dep_flag] = \
                    re.sub(":\s+", "", sectTemplate.search(line).group(0))
            return dep_flag
    if dep_flag in dep_sects_list:
        entry_list = [it.start() for it in package_with_version.finditer(line)]
        for pack_idx in entry_list:
            pack = package_with_version.search(line[pack_idx:]).group(0)
            pack_name = packageName.search(pack)
            pack_eq = packageEq.search(pack)
            pack_ver = packageVers.search(pack)
            # weak place: if (<< 0.5 | >> 0.7) will be != 0.5
            # instead of range != 0.5, != 0.6, != 0.7
            if package_ver_not_equal.search(pack):
                pack_eq = "!="
            if section_dict["Package"][cur_package][dep_flag].has_key(pack_name):
                section_dict["Package"][cur_package][dep_flag][pack_name]. \
                    add((pack_eq, pack_ver))
            else:
                section_dict["Package"][cur_package][dep_flag][pack_name] = \
                    {(pack_eq, pack_ver)}
    elif dep_flag != "":
        section_dict["Package"][cur_package][dep_flag] += "\n{0}".format(line)
    return dep_flag

def load_control(control_file_name = "control"):
    try:
        with open(recur_search(control_file_name), 'r') as control_file:
            cur_package = dep_flag = ""
            for line in control_file:
                if not cur_package:
                    for main_sect in main_section_list:
                        if main_sect in line and not section_dict[main_sect] and \
                            main_sect not in build_dep_sects_list:
                            section_dict[main_sect] = re.sub(":\s+", "",
                                sectTemplate.search(line).group(0))
                else:
                    dep_flag = parse_packages(line, dep_flag, cur_package)
                if "Package:" in line:
                    cur_package = re.sub(":\s+", "",
                        sectTemplate.search(line).group(0))
    except IOError:
        print "There is no control file!"


def generate_control(control_file_name = "control"):

    def write_packs(sect):
        for pack_el, pack_val in sect.iteritems():
            if pack_el:
                if pack_val:
                    for dep_el in pack_val:
                        if dep_el[0] == "!=":
                            control_file.write(" {0} (<< {1}) | {0} (>> {1})," \
                                .format(pack_el, dep_el[1]))
                        else:
                            control_file.write(" {0} ({1} {2})," \
                                .format(pack_el, dep_el[0], dep_el[1]))
                else:
                    control_file.write(" {0},".format(pack_el))
            control_file.write("\n")

    try:
        with open(recur_search(control_file_name), "w+") as control_file:
            for main_sect in main_section_list:
                if section_dict[main_sect] and section_dict.has_key(main_sect):
                    if main_sect in build_dep_sects_list:
                        control_file.write("{0}:\n".format(main_sect))
                        write_packs(section_dict[main_sect])
                    else:
                        control_file.write("{0}: {1}\n".format(main_sect, section_dict[main_sect]))
            for pack, value in section_dict["Package"].iteritems():
                control_file.write("\nPackage: {0}\n".format(pack))
                for pack_sect in package_section_list:
                    if value[pack_sect]:
                        if pack_sect in dep_sects_list:
                            control_file.write("{0}:\n".format(pack_sect))
                            write_packs(value[pack_sect])
                        else:
                            control_file.write("{0}: {1}\n".format(pack_sect, value[pack_sect]))
    except (IOError, TypeError):
        print "Error while overwriting control file!"

def generate_rules(build_system, build_with, rules_file_name = "rules"):
    try:
        content = []
        with open(recur_search(rules_file_name), "r") as rules_file:
            for line in rules_file.readlines():
                if "dh $@" in line:
                    res_line = line
                    if build_system and build_with:
                        res_line = line.rstrip() + " --buildsystem={0} --with {1}".format(build_system, build_with)
                    elif build_system:
                        res_line = line.rstrip() + " --buildsystem={0}".format(build_system)
                    content.append(res_line)
                else:
                    content.append(line)

        with open(recur_search(rules_file_name), "w+") as rules_file:
            rules_file.writelines(content)

    except IOError:
        print "Error while overwriting rules file!"

main()