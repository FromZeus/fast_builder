import json
import lan
import re
import require_utils
from os import listdir
from os.path import join, isdir

package_with_version = \
  re.compile("(([a-zA-Z0-9-_.])|(\$\{[^\s]*\}))+\s*(\([^,]*\)){,1}" \
    "(\s*\|{1}\s*[a-zA-Z0-9-_.]+\s*(\([^,]*\))*){,1},")
package_ver_not_equal = re.compile("\(.*(<<).*\|.*(>>).*\)")
packageName = re.compile("([a-zA-Z0-9-_.]+|(\$\{[^\s]*\})+)")
packageEq = re.compile("(>=|<=|>>|<<|!=|=)+")
packageVers = re.compile("((\d[.a-z+-~:]*)+|(\$\{[^\s]*\})+)")
packageEpoch = re.compile("\d:")
impTemplate = re.compile("import [a-zA-Z0-9-_.]+")
fromTemplate = re.compile("from [a-zA-Z0-9-_.]+")
packageNameEnd = re.compile("[a-zA-Z0-9-_.]+$")
build_depends = re.compile("((\"[a-zA-Z0-9-_.]+\")|(\'[a-zA-Z0-9-_.]+\'))")

def none_check(obj):
  return obj if obj else ""

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

def part_of_package(package, packages):
  for el in packages:
    if el in package:
      return el
  return None

def in_pack_ver(line, pack_val):
  for eq, ver in pack_val:
    if line in ver:
      return line
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

def update_depends(depends, global_req, not_update):
  new_depends = dict([(pack_name, global_req[pack_name])
    if global_req.has_key(pack_name) and pack_name not in not_update \
    and not in_pack_ver("$", pack_val) else (pack_name, pack_val)
      for pack_name, pack_val in depends.iteritems()])
  return new_depends

def exclude_excepts(depends, excepts):
  for el in excepts:
    if depends.has_key(el):
      del depends[el]

def filter_bounds(section_in_dict, del_bounds_list):
  for pack_name in section_in_dict.keys():
    section_in_dict[pack_name] = set(dep_el
      for dep_el in section_in_dict[pack_name]
        if dep_el[0] not in del_bounds_list)

def synchronize_with_onlyif(section_in_dict, name):
  for pack_name, pack_val in section_in_dict["OnlyIf-{0}".format(name)].iteritems():
    if section_in_dict[name].has_key(pack_name):
      section_in_dict[name][pack_name] = pack_val

def separate_onlyif_section(section):
  new_section = dict((pack_name, pack_val) for pack_name, pack_val in
    section.iteritems() if pack_name != "OnlyIf")
  if new_section:
    packages_processing(new_section)
  return new_section

def packages_processing(section_in_dict):
  for el in section_in_dict.keys():
    section_in_dict[el] = {(el1.items()[0]) for el1 in section_in_dict[el]}

def add_epoch(gerrit_account, epoch_dict, pack_name, pack_val, branch):
  if epoch_dict.has_key(pack_name):
    epoch = epoch_dict[pack_name]
  else:
    epoch = get_epoch(gerrit_account, pack_name, branch)
    if not epoch and pack_name.startswith("python-"):
      epoch = get_epoch(gerrit_account, re.sub("python-", "", pack_name), branch)
    epoch_dict[pack_name] = epoch

  new_pack_val = pack_val
  if epoch:
    new_pack_val = [(pack_eq, epoch + pack_ver)
    for pack_eq, pack_ver in pack_val]

  return new_pack_val

def check_epoch(section_in_dict, epoch_dict, gerrit_account, branch):
  new_section = dict([(pack_name, add_epoch(gerrit_account, epoch_dict, pack_name, pack_val, branch))
    for pack_name, pack_val in section_in_dict.iteritems()])
  return new_section

def get_epoch(gerrit_account, pack_name, branch):
  req_changelog = request_file(gerrit_account, pack_name, branch, "changelog")

  epoch_line = ""
  if req_changelog is not None:
    epoch_line = require_utils.Require.get_epoch(req_changelog)

  if epoch_line:
    epoch = packageEpoch.search(epoch_line).group(0)
    return epoch
  else:
    return None

def get_build_dependencies(build_depends, global_req, control_base, py_file_names = ["setup.py"]):
  for py_file in py_file_names:
    path_to_py = recur_search(names = py_file)
    packets_from_py = load_packs(path_to_py, control_base)
    if packets_from_py:
      build_depends = dict(build_depends.items() + packets_from_py.items())
    else:
      print "There is no any of .py file with build dependencies!"

  return build_depends

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

def request_file(gerrit_account, repo, branch, type):
    # URL for getting changelog file
    req_url_changelog = ['https://review.fuel-infra.org/gitweb?p=openstack-build/{0}-build.git;' \
                        'a=blob_plain;f=debian/{2};hb=refs/heads/{1}',
                        'https://review.fuel-infra.org/gitweb?p=openstack-build/{0}-build.git;' \
                        'a=blob_plain;f=trusty/debian/{2};hb=refs/heads/{1}']

    idx = 0 
    while idx < len(req_url_changelog):
        try:
            req_control = \
                lan.get_requirements_from_url(req_url_changelog[idx].format(repo.strip(), branch, type),
                    gerrit_account)
        except KeyError:
            req_control = None
        idx += 1
        if req_control is not None:
            break

    return req_control

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

def parse_packages(line):
  res = dict()
  entry_list = [it.start() for it in package_with_version.finditer(line)]
  for pack_idx in entry_list:
    pack = package_with_version.search(line[pack_idx:]).group(0)
    pack_name = pack_eq = pack_ver = ""
    if "|" in pack:
      pack_name1 = packageName.search(pack).group(0)
      pack_name2 = packageName.search(pack[pack.index("|"):]).group(0)
      if pack_name1 != pack_name2:
        pack_name = re.sub("\s*,", "", pack)
    if not pack_name:
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

def normalize(depends,
  base_control,
  control_base,
  control_internal,
  control_internal_check,
  unknown_file
  ):

  def write_unknown(unknown_packages, unknown_file):
    if unknown_packages:
      try:
        unknown_file.seek(0)
        packages = json.load(unknown_file)
      except ValueError:
        packages = dict()

      unknown_file.seek(0)
      json.dump(dict(unknown_packages.items() + packages.items()), unknown_file,
        indent=4, sort_keys=True, separators=(',', ':'))
      unknown_file.truncate()

  if not depends:
    depends = dict()
  new_depends = dict([(base_control[pack_name], {format_sign(el) for el in pack_val})
    if check_in_base(base_control, pack_name) else
      (pack_name, {format_sign(el) for el in pack_val})
      if check_in_base(control_base, pack_name) or check_in_base(control_internal, pack_name)
      and not control_internal_check else
        (control_internal[pack_name], {format_sign(el) for el in pack_val})
        if check_in_base(control_internal, pack_name) else
        (pack_name, pack_val)
        if "|" in pack_name else (pack_name, "unknown")
          for pack_name, pack_val in depends.iteritems()])

  unknown_packages = dict()
  _new_depends = dict()
  for pack_name, pack_val in new_depends.iteritems():
    if pack_val == "unknown":
      print "Unknown package: {0}".format(pack_name)
      unknown_packages[pack_name] = pack_name
    else:
      _new_depends[pack_name] = pack_val

  write_unknown(unknown_packages, unknown_file)

  return _new_depends

def filter_packs(line, control_base):
  req_pack = build_depends.search(line)
  imp = impTemplate.search(line)
  frm = fromTemplate.search(line)

  entry_list = [(it.start(), it.end()) for it in build_depends.finditer(line)]

  for (entry_start, entry_end) in entry_list:
    req_pack_name = line[entry_start + 1:entry_end - 1:]
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

  if imp or frm:
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

# def depends_to_orline(depends):
#   orline = ""
#   for pack_name, pack_val in depends.iteritems():
#     orline += generate_out_pack(pack_name, pack_val)

# def update_dependency(pack_name, pack_val, global_req, not_update):
#   if "|" in pack_name:
#     depends = parse_packages(re.sub("|", "," pack_name))
#     depends = update_depends(depends, global_req, not_update)
#     new_pack_name = 
#     return (rnew_pack_namees, pack_val)
#   else:
#     return (pack_name, pack_val)