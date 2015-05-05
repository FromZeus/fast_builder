import yaml
from os.path import join, isdir
from os import listdir
from os import system
import argparse
import pdb
import lan
import require_utils
import re
import json

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config', dest='config', help='Configuration YAML')
args = parser.parse_args()

packageName = re.compile("(\d*[a-zA-Z0-9-_.]\d*)+")
packageEq = re.compile("(>=|<=|>>|<<|==|!=)+")
packageVers = re.compile("(\d[.]*[a-z+-~:]*)+")
pacakgeRevis = re.compile("[0-9.a-z+-~:]+")
packageVersChangelog = re.compile("(\d[.]*[a-z]*)+")
packageNameEnd = re.compile("[a-zA-Z0-9-_.]+$")
impTemplate = re.compile("import [a-zA-Z0-9-_.]+")
fromTemplate = re.compile("from [a-zA-Z0-9-_.]+")
sectTemplate = re.compile(":.+")
build_depends = re.compile('"[a-zA-Z0-9-_.|<|>|=|!]+"')
package_with_version = \
  re.compile("[a-zA-Z0-9-_.]+\s*(\((\s*(>>|<<|==|>=|<=)+\s*(\d[.]*[a-z+-~:]*)+\s*)\)){,1}" \
    "(\s*\|{1}\s*[a-zA-Z0-9-_.]+\s*\((\s*(>>|<<|==|>=|<=)+\s*(\d[.]*[a-z+-~:]*)+\s*)\)){,1},")
package_ver_not_equal = re.compile("\(.*(<<).*\|.*(>>).*\)")
cap_of_changelog = re.compile("[a-zA-Z0-9-_.]+\s*\((\d[.]*[a-z]*)+(\d[.]*[a-z+-~:]*)*\)" \
  "\s*[a-zA-Z0-9-_.]+\s*;\s*urgency=[a-z]+")

base_depends = {"${shlibs:Depends}": {}, "${misc:Depends}": {}}
build_excepts = {"python-distutils.core" : {}, "python-sys" : {}, "python-setup" : {},
  "python-argparse" : {}, "python-ordereddict" : {},
  "python-multiprocessing": {}, "python-os": {}}

build_dep_sects_list = ["Build-Depends", "Build-Depends-Indep", "Build-Conflicts"]
dep_sects_list = ["Pre-Depends", "Depends", "Conflicts", "Provides", "Breaks",
"Replaces", "Recommends", "Suggests"]
def_main_section_list = ["Source", "Section", "Priority", "Maintainer",
"XSBC-Original-Maintainer", "Uploaders", "X-Python-Version", "Standards-Version",
"Homepage", "Vcs-Svn", "Vcs-Browser"]
def_package_section_list = ["Architecture", "Section", "Description"]
main_section_list = ["Source", "Section", "Priority", "Maintainer",
"XSBC-Original-Maintainer", "Uploaders", "X-Python-Version", "Build-Depends",
"Build-Depends-Indep", "Standards-Version", "Homepage", "Vcs-Svn", "Vcs-Browser", "XS-Testsuite"]
package_section_list = ["Architecture", "Section", "Pre-Depends", "Depends", "Conflicts",
"Provides", "Breaks", "Replaces", "Recommends", "Suggests", "Description"]
changelog_sects = ["PakageName", "Version", "Revision", "Tag", "Urgency"]
section_dict = dict()
user_defined_in_main = set()
user_defined_in_packets = dict()
packs_without_bounds = set()

def main():
  pdb.set_trace()
  try:
    conf = open(args.config, 'r')
    tempConf = yaml.load_all(conf)

    control_base_file = open("control-base.json", "r")
    base_control_file = open("base-control.json", "r")
    control_internal_file = open("control-internal.json", "r")
    control_base = json.load(control_base_file)
    base_control = json.load(base_control_file)
    control_internal = json.load(control_internal_file)

    for line in tempConf:
      depends = dict()
      build_depends = dict()

      launchpad_id = line["Login"]
      launchpad_pw = line["Password"]
      global_branch = line["Branch"]

      del_bounds_list = line["DelBounds"]
      control_internal_check = line["ControlInternal"]
      update_if_bounds = line["UpdateIfBounds"]

      if global_branch == 'master':
        global_branch = 'master'
      elif global_branch == 'juno':
        global_branch = 'stable/juno'
      elif global_branch == 'icehouse':
        global_branch = 'stable/icehouse'
      elif global_branch == 'kilo':
        global_branch = 'stable/kilo'
      gerritAccount = lan.login_to_launchpad(launchpad_id, launchpad_pw)

      req_url = 'https://raw.githubusercontent.com/openstack/requirements/' \
      '{0}/global-requirements.txt'.format(global_branch)
      global_req = require_utils.Require.parse_req(
        lan.get_requirements_from_url(req_url, gerritAccount))
      print "Normalize global requirements..."
      normalized_global_req = normalize(global_req, base_control, control_base,
        control_internal, control_internal_check)
      print "Global requirements has been normalized successfully!"

      section_dict["Update"] = line["Update"]

      section_dict["Source"] = line["Source"]
      section_dict["Section"] = line["Section"]
      section_dict["Priority"] = line["Priority"]
      section_dict["Maintainer"] = line["Maintainer"]
      section_dict["XSBC-Original-Maintainer"] = line["XSBC-Original-Maintainer"]
      section_dict["Uploaders"] = line["Uploaders"]

      def separate_onlyif_section(section):
        new_section = dict((pack_name, pack_val) for pack_name, pack_val in
          section.iteritems() if pack_name != "OnlyIf")
        if new_section:
          packages_processing(new_section)
        return new_section

      build_excepts[section_dict["Source"]] = {}

      section_dict["OnlyIf-Build-Depends"] = section_dict["OnlyIf-Build-Depends-Indep"] = \
        section_dict["OnlyIf-Build-Conflicts"] = dict()

      for sect in build_dep_sects_list:
        section_dict[sect] = line[sect]
        if line[sect]:
          section_dict[sect] = separate_onlyif_section(section_dict[sect])
          if line[sect].has_key("OnlyIf"):
            section_dict["OnlyIf-{0}".format(sect)] = line[sect]["OnlyIf"]
            packages_processing(section_dict["OnlyIf-{0}".format(sect)])
      
      #-------------------------------------------------------------#

      section_dict["X-Python-Version"] = line["X-Python-Version"]
      section_dict["Standards-Version"] = line["Standards-Version"]
      section_dict["Homepage"] = line["Homepage"]
      section_dict["Vcs-Svn"] = line["Vcs-Svn"]
      section_dict["Vcs-Browser"] = line["Vcs-Browser"]
      section_dict["XS-Testsuite"] = line["XS-Testsuite"]

      section_dict["Package"] = line["Package"]

      path_to_debian_dir = recur_search("debian")
      for pack_name, pack_val in section_dict["Package"].iteritems():
        if pack_val["Files"]:
          with open(join(path_to_debian_dir, "{0}.install".format(pack_name)), 
            "w+") as pack_install:
            pack_install.writelines(re.sub(";\s*", "\n", pack_val["Files"]))

      build_system = line["Buildsystem"]
      build_with = line["BuildWith"]

      for sect in changelog_sects:
        section_dict[sect] = line[sect]

      for el in def_main_section_list:
        if section_dict[el]:
          user_defined_in_main.add(el)
      for pack_name, pack_val in section_dict["Package"].iteritems():
        user_defined_in_packets[pack_name] = set()
        for el in def_package_section_list:
          if pack_val[el]:
            user_defined_in_packets[pack_name].add(el)

      #section_dict["Build-Depends"] = get_build_dependencies(section_dict["Build-Depends"],
      #  normalized_global_req, control_base)
      section_dict["Build-Depends-Indep"] = get_build_dependencies(section_dict["Build-Depends-Indep"],
        normalized_global_req, control_base)

      for pack_name in section_dict["Package"].keys():
        build_excepts[pack_name] = {}
        for dep_sect in dep_sects_list:
          section_dict["Package"][pack_name]["OnlyIf-{0}".format(dep_sect)] = dict()
          if section_dict["Package"][pack_name][dep_sect]:
            if section_dict["Package"][pack_name][dep_sect].has_key("OnlyIf"):
              section_dict["Package"][pack_name]["OnlyIf-{0}".format(dep_sect)] = \
                section_dict["Package"][pack_name][dep_sect]["OnlyIf"]
              packages_processing(section_dict["Package"][pack_name]["OnlyIf-{0}".format(dep_sect)])
            section_dict["Package"][pack_name][dep_sect] = \
              separate_onlyif_section(section_dict["Package"][pack_name][dep_sect])

            section_dict["Package"][pack_name]["OnlyIf-{0}".format(dep_sect)] = \
              normalize(section_dict["Package"][pack_name]["OnlyIf-{0}".format(dep_sect)],
                base_control, control_base, control_internal, control_internal_check)
            section_dict["Package"][pack_name][dep_sect] = \
              normalize(section_dict["Package"][pack_name][dep_sect],
                base_control, control_base, control_internal, control_internal_check)

        section_dict["Package"][pack_name]["Depends"] = \
          add_base_depends(section_dict["Package"][pack_name]["Depends"])
        if section_dict["Package"][pack_name]["Main"]:
          section_dict["Package"][pack_name]["Depends"] = \
            get_dependencies(section_dict["Package"][pack_name]["Depends"], global_req, base_control)

      load_control()

      for sect in build_dep_sects_list:
        section_dict[sect] = normalize(section_dict[sect],
          base_control, control_base, control_internal, control_internal_check)
        section_dict["OnlyIf-{0}".format(sect)] = normalize(section_dict["OnlyIf-{0}".format(sect)],
          base_control, control_base, control_internal, control_internal_check)
        if update_if_bounds:
          for pack_name, pack_val in section_dict[sect].iteritems():
            if not pack_val:
              packs_without_bounds.add(pack_name)

      exclude_excepts(section_dict["Build-Depends-Indep"], build_excepts)
      exclude_excepts(section_dict["Build-Depends"], build_excepts)

      if section_dict["Update"]:
        section_dict["Build-Depends"] = update_depends(section_dict["Build-Depends"],
          normalized_global_req, section_dict["OnlyIf-Build-Depends"].keys() + list(packs_without_bounds))
        section_dict["Build-Depends-Indep"] = update_depends(section_dict["Build-Depends-Indep"],
          normalized_global_req, section_dict["OnlyIf-Build-Depends-Indep"].keys() + list(packs_without_bounds))


      for sect in build_dep_sects_list:
        synchronize_with_onlyif(section_dict, sect)
        if section_dict[sect]:
          filter_bounds(section_dict[sect], del_bounds_list)

      packs_without_bounds.clear()

      for pack_name in section_dict["Package"].keys():
        for dep_sect in dep_sects_list:

          if section_dict["Package"][pack_name][dep_sect]:
            synchronize_with_onlyif(section_dict["Package"][pack_name], dep_sect)
            section_dict["Package"][pack_name][dep_sect] = \
              normalize(section_dict["Package"][pack_name][dep_sect],
                base_control, control_base, control_internal, control_internal_check)

            if section_dict["Update"]:

              if update_if_bounds:
                for _pack_name, _pack_val in section_dict["Package"][pack_name][dep_sect].iteritems():
                  if not _pack_val:
                    packs_without_bounds.add(_pack_name)

              section_dict["Package"][pack_name][dep_sect] = \
                update_depends(section_dict["Package"][pack_name][dep_sect], normalized_global_req,
                  section_dict["Package"][pack_name]["OnlyIf-{0}".format(dep_sect)].keys() + \
                    list(packs_without_bounds))
            filter_bounds(section_dict["Package"][pack_name][dep_sect], del_bounds_list)

        if not section_dict["Package"][pack_name]["Architecture"]:
          section_dict["Package"][pack_name]["Architecture"] = "any"
        if not section_dict["Package"][pack_name]["Description"]:
          section_dict["Package"][pack_name]["Description"] = "<insert up to 60 chars description>\n" \
            " <insert long description, indented with spaces>"

      generate_control()
      generate_rules(build_system, build_with)
      generate_changelog(section_dict)

    control_base_file.close()
    base_control_file.close()
    control_internal_file.close()
    conf.close()

  except KeyboardInterrupt:
    print '\nThe process was interrupted by the user'
    raise SystemExit

def synchronize_with_onlyif(section_in_dict, name):
  for pack_name, pack_val in section_in_dict["OnlyIf-{0}".format(name)].iteritems():
    if section_in_dict[name].has_key(pack_name):
      section_in_dict[name][pack_name] = pack_val

def packages_processing(section_in_dict):
  for el in section_in_dict.keys():
    section_in_dict[el] = {(el1.items()[0]) for el1 in section_in_dict[el]}

def normalize(depends, base_control, control_base, control_internal, control_internal_check):
  if not depends:
    depends = dict()
  new_depends = dict([(base_control[pack_name], {format_sign(el) for el in pack_val})
    if check_in_base(base_control, pack_name) else
      (pack_name, {format_sign(el) for el in pack_val})
      if check_in_base(control_base, pack_name) or pack_name in base_depends.keys()
      or check_in_base(control_internal, pack_name) and not control_internal_check else
        (control_internal[pack_name], {format_sign(el) for el in pack_val})
        if check_in_base(control_internal, pack_name) else (pack_name, "unknown")
          for pack_name, pack_val in depends.iteritems()])

  _new_depends = dict()
  for pack_name, pack_val in new_depends.iteritems():
    if pack_val == "unknown":
      print "Unknown package: {0}".format(pack_name)
    else:
      _new_depends[pack_name] = pack_val

  return _new_depends

# Change "reuirements" style to "control" style signs and update requirements
def update_depends(depends, global_req, not_update):
  new_depends = dict([(pack_name, global_req[pack_name])
    if global_req.has_key(pack_name) and  pack_name not in not_update else (pack_name, pack_val)
      for pack_name, pack_val in depends.iteritems()])
  return new_depends

def exclude_excepts(depends, excepts):
  for el in excepts:
    if depends.has_key(el):
      del depends[el]

def get_build_dependencies(build_depends, global_req, control_base, py_file_names = ["setup.py"]):
  for py_file in py_file_names:
    path_to_py = recur_search(names = py_file)
    packets_from_py = load_packs(path_to_py, control_base)
    if packets_from_py:
      build_depends = dict(build_depends.items() + packets_from_py.items())
    else:
      print "There is no any of .py file with build dependencies!"

  return build_depends

def add_base_depends(depends):
  if not depends:
    depends = dict()
  depends = dict(depends.items() + base_depends.items())
  return depends

def get_dependencies(depends,
  global_req,
  base_control,
  req_file_names = ["requires.txt", "requirements.txt"]):

  try:
    with open(recur_search(req_file_names), 'r') as req_file:
      for pack_name, pack_val in require_utils.Require.parse_req(req_file).iteritems():
        base_el = check_in_base(base_control, pack_name)
        base_el = (check_in_base(base_control, re.sub("-", "_", pack_name))
          if not base_el else base_el)
        base_el = (check_in_base(base_control, re.sub("_", "-", pack_name))
          if not base_el else base_el)
        if base_el:
          depends.setdefault(base_control[base_el], pack_val)
        else:
          print "Unknown package in requirements file: {0}".format(pack_name)
  except (IOError, TypeError):
    print "There is no requirements!"
  return depends

def check_in_base(base, el):
  if base.has_key(el):
    return el
  else:
    return None

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
  except (IOError, TypeError):
    return None

def recur_search(names, relative_path = "."):
  for el in listdir(relative_path):
    if el in names:
      return join(relative_path, el)
    elif isdir(join(relative_path, el)) and el not in ["doc", ".git"]:
      path = recur_search(names, join(relative_path, el))
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
        print "Unknown package in .py file: {0}".format(res_pack_name)
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
      print "Unknown package in .py file: {0}".format(res_pack_name_imp)
    elif res_pack_name_frm and not res_pack_name_frm_part:
      print "Unknown package in .py file: {0}".format(res_pack_name_frm_part)
  return None

def part_of_package(package, packages):
  for el in packages:
    if el in package:
      return el
  return None

def parse_packages(line):
  res = dict()
  entry_list = [it.start() for it in package_with_version.finditer(line)]
  for pack_idx in entry_list:
    pack = package_with_version.search(line[pack_idx:]).group(0)
    pack_name = packageName.search(pack).group(0)
    pack = pack[len(pack_name):]
    pack_eq = packageEq.search(pack)
    if pack_eq:
      pack_eq = pack_eq.group(0)
    pack_ver = packageVers.search(pack)
    if pack_ver:
      pack_ver = pack_ver.group(0)
    # weak place: if (<< 0.5 | >> 0.7) will be != 0.5
    # instead of range != 0.5, != 0.6, != 0.7
    if package_ver_not_equal.search(pack):
      pack_eq = "!="
    res.setdefault(pack_name, set())
    if pack_eq and pack_ver:
      res[pack_name].add((pack_eq, pack_ver))
  return res

def load_control(control_file_name = "control"):

  def add_to_sect(cur_sect, dep_sects_list, section_in_dict, line):
    if cur_sect in dep_sects_list:
      packs_in_line = parse_packages(line)
      if not section_in_dict[cur_sect]:
        section_in_dict[cur_sect] = dict()
      for pack_name, pack_val in packs_in_line.iteritems():
        #if pack_name not in section_in_dict["OnlyIf-{0}".format(cur_sect)].keys():
        section_in_dict[cur_sect].setdefault(pack_name, pack_val)
        section_in_dict[cur_sect][pack_name] |= pack_val
        #else:
        #  section_in_dict[cur_sect][pack_name] = \
        #    section_in_dict["OnlyIf-{0}".format(cur_sect)][pack_name]
    else:
        sect_templ_line = sectTemplate.search(line)
        new_line = ""
        if sect_templ_line:
          new_line = re.sub(":\s+", "", sect_templ_line.group(0))
        elif line.startswith(" "):
          new_line = line
        section_in_dict[cur_sect] = (section_in_dict[cur_sect] +
          "\n{0}".format(new_line.rstrip()) if section_in_dict[cur_sect] else new_line)

  try:
    with open(recur_search(control_file_name), 'r') as control_file:
      cur_package = cur_sect = ""
      for line in control_file:
        if line.startswith("#"):
          continue
        if "Package:" in line:
          cur_package = re.sub(":\s+", "",
            sectTemplate.search(line).group(0))
          continue
        if not cur_package:
          for package_sect in main_section_list:
            if "{0}:".format(package_sect) in line:
              cur_sect = package_sect
              break
          if cur_sect not in user_defined_in_main:
            add_to_sect(cur_sect, build_dep_sects_list, section_dict, line)
        else:
          for package_sect in package_section_list:
            if "{0}:".format(package_sect) in line:
              cur_sect = package_sect
              break
          if cur_sect not in user_defined_in_packets[cur_package]:
            add_to_sect(cur_sect, dep_sects_list,
              section_dict["Package"][cur_package], line)
  except (IOError, TypeError):
    print "There is no control file!"


def filter_bounds(section_in_dict, del_bounds_list):
  for pack_name in section_in_dict.keys():
    section_in_dict[pack_name] = set(dep_el
      for dep_el in section_in_dict[pack_name]
        if dep_el[0] not in del_bounds_list)

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
            res_line = line.rstrip() + " --buildsystem={0} --with {1}".format(build_system,
              build_with)
          elif build_system:
            res_line = line.rstrip() + " --buildsystem={0}".format(build_system)
          content.append(res_line)
        else:
          content.append(line)

    with open(recur_search(rules_file_name), "w+") as rules_file:
      rules_file.writelines(content)

  except (IOError, TypeError):
    print "Error while overwriting rules file!"

def generate_changelog(section_dict, changelog_file_name = "changelog"):
  try:
    content = []
    with open(recur_search(changelog_file_name), "r") as changelog_file:
      for line in changelog_file.readlines():
        cap = cap_of_changelog.search(line)
        if cap:
          cap_line = cap.group(0)
          pack_name = packageName.search(cap_line)
          pack_name = pack_name.group(0)
          section_dict.setdefault("PakageName", pack_name)

          cap_line = cap_line[len(pack_name):]
          pack_ver_idx = [(it.start(), it.end()) for it in
            packageVersChangelog.finditer(cap_line)]
          pack_ver = cap_line[pack_ver_idx[0][0]:pack_ver_idx[0][1]]
          section_dict.setdefault("Version", pack_ver)

          cap_line = cap_line[pack_ver_idx[0][1]:]
          pack_revis_idx = [(it.start(), it.end()) for it in
            pacakgeRevis.finditer(cap_line)]
          if not pack_revis_idx:
            pack_revis_idx = pack_ver_idx
          pack_revis = cap_line[pack_revis_idx[0][0]:pack_revis_idx[0][1]]
          section_dict.setdefault("Revision", pack_revis)

          cap_line = cap_line[pack_revis_idx[0][1]:]
          pack_tag_idx = [(it.start(), it.end()) for it in
            packageName.finditer(cap_line)]
          pack_tag = cap_line[pack_tag_idx[0][0]:pack_tag_idx[0][1]]
          section_dict.setdefault("Tag", pack_tag)

          cap_line = cap_line[pack_tag_idx[0][1]:]
          pack_urgency_idx = [(it.start(), it.end()) for it in
            re.finditer("urgency", cap_line)]
          pack_urgency = re.search("[a-z]+", cap_line[pack_urgency_idx[0][1]:])
          pack_urgency = pack_urgency.group(0)
          section_dict.setdefault("Urgency", pack_urgency)

      content.append("{0} ({1}{2}) {3}; urgency={4}\n".format(section_dict["PakageName"],
        section_dict["Version"], section_dict["Revision"], section_dict["Tag"], section_dict["Urgency"]))
      content.append("\n  * Generated by FastBuilder\n")
      content.append("\n -- {0}  {1}\n\n".format(section_dict["Maintainer"], system("date -R")))

    with open(recur_search(changelog_file_name), "w+") as changelog_file:
      for line in changelog_file.readlines():
        content.append(line)
      changelog_file.writelines(content)

  except (IOError, TypeError):
    print "Error while overwriting changelog file!"

main()