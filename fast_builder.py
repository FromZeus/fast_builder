import yaml
from os import system
import argparse
import pdb
import lan
import require_utils
import re
import json
from os.path import join, isdir
import fast_builder_loader
import fast_builder_tools
import fast_builder_generator

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config', dest='config', help='Configuration YAML')
args = parser.parse_args()

build_dep_sects_list = ["Build-Depends", "Build-Depends-Indep", "Build-Conflicts"]
dep_sects_list = ["Pre-Depends", "Depends", "Conflicts", "Provides", "Breaks",
"Replaces", "Recommends", "Suggests"]
not_update_dep_list = ["Conflicts", "Provides", "Breaks",
"Replaces", "Recommends", "Suggests"]
def_main_section_list = ["Source", "Section", "Priority", "Maintainer",
"XSBC-Original-Maintainer", "Uploaders", "X-Python-Version", "Standards-Version",
"Homepage", "Vcs-Svn", "Vcs-Browser"]
def_package_section_list = ["Architecture", "Section", "Description"]
main_section_list = ["Source", "Section", "Priority", "Maintainer",
"XSBC-Original-Maintainer", "Uploaders", "X-Python-Version", "Build-Depends",
"Build-Depends-Indep", "Standards-Version", "Homepage", "Vcs-Svn", "Vcs-Arch", "Vcs-Bzr",
"Vcs-Cvs", "Vcs-Darcs", "Vcs-Git", "Vcs-Hg", "Vcs-Mtn", "Vcs-Browser", "XS-Testsuite"]
package_section_list = ["Architecture", "Section", "Pre-Depends", "Depends", "Conflicts",
"Provides", "Breaks", "Replaces", "Recommends", "Suggests", "Description"]
changelog_sects = ["PakageName", "Version", "Revision", "Tag", "Urgency"]

section_dict = dict()
user_defined_in_main = set()
user_defined_in_packets = dict()
packs_without_bounds = set()
epoch_dict = dict()

def main():
  #pdb.set_trace()
  try:
    conf = open(args.config, 'r')
    tempConf = yaml.load_all(conf)

    control_base_file = open("control-base.json", "r+")
    base_control_file = open("base-control.json", "r+")
    control_internal_file = open("control-internal.json", "r")

    unknown_req_file = open("unknown_req.json", "r+")
    unknown_req_file.seek(0)
    json.dump({}, unknown_req_file, indent=4, sort_keys=True, separators=(',', ':'))
    unknown_req_file.truncate()

    unknown_dep_file = open("unknown_dep.json", "r+")
    unknown_dep_file.seek(0)
    json.dump({}, unknown_dep_file, indent=4, sort_keys=True, separators=(',', ':'))
    unknown_dep_file.truncate()

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
      if not del_bounds_list:
        del_bounds_list = []
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

      branch = ""
      if global_branch == 'master':
        branch = 'master'
      elif global_branch == 'stable/juno':
        branch = 'openstack-ci/fuel-6.1/2014.2'
      elif global_branch == 'stable/icehouse':
        branch = 'openstack-ci/fuel-6.0.1/2014.2'
      elif global_branch == 'stable/kilo':
        branch = 'openstack-ci/fuel-7.0/2015.1.0'

      req_url = 'https://raw.githubusercontent.com/openstack/requirements/' \
      '{0}/global-requirements.txt'.format(global_branch)
      global_req = require_utils.Require.parse_req(
        lan.get_requirements_from_url(req_url, gerritAccount))
      print "Normalize global requirements..."
      normalized_global_req = fast_builder_tools.normalize(global_req, base_control, control_base,
        control_internal, control_internal_check, unknown_req_file)
      print "Global requirements has been normalized successfully!"

      section_dict["Update"] = line["Update"]
      section_dict["SetEpoch"] = line["SetEpoch"]

      section_dict["Source"] = line["Source"]
      section_dict["Section"] = line["Section"]
      section_dict["Priority"] = line["Priority"]
      section_dict["Maintainer"] = line["Maintainer"]
      section_dict["XSBC-Original-Maintainer"] = line["XSBC-Original-Maintainer"]
      section_dict["Uploaders"] = line["Uploaders"]

      build_excepts = line["BuildExcepts"]
      build_excepts[section_dict["Source"]] = {}

      section_dict["OnlyIf-Build-Depends"] = section_dict["OnlyIf-Build-Depends-Indep"] = \
        section_dict["OnlyIf-Build-Conflicts"] = dict()

      for sect in build_dep_sects_list:
        section_dict[sect] = line[sect]
        if line[sect]:
          section_dict[sect] = fast_builder_tools.separate_onlyif_section(section_dict[sect])
          if line[sect].has_key("OnlyIf"):
            section_dict["OnlyIf-{0}".format(sect)] = line[sect]["OnlyIf"]
            fast_builder_tools.packages_processing(section_dict["OnlyIf-{0}".format(sect)])
      
      #-------------------------------------------------------------#

      section_dict["X-Python-Version"] = line["X-Python-Version"]
      section_dict["Standards-Version"] = line["Standards-Version"]
      section_dict["Homepage"] = line["Homepage"]
      section_dict["Vcs-Svn"] = line["Vcs-Svn"]
      section_dict["Vcs-Arch"] = line["Vcs-Arch"]
      section_dict["Vcs-Bzr"] = line["Vcs-Bzr"]
      section_dict["Vcs-Cvs"] = line["Vcs-Cvs"]
      section_dict["Vcs-Darcs"] = line["Vcs-Darcs"]
      section_dict["Vcs-Git"] = line["Vcs-Git"]
      section_dict["Vcs-Hg"] = line["Vcs-Hg"]
      section_dict["Vcs-Mtn"] = line["Vcs-Mtn"]
      section_dict["Vcs-Browser"] = line["Vcs-Browser"]
      section_dict["XS-Testsuite"] = line["XS-Testsuite"]

      section_dict["Package"] = line["Package"]

      path_to_debian_dir = fast_builder_tools.recur_search("debian")
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
      section_dict["Build-Depends-Indep"] = fast_builder_tools.get_build_dependencies(section_dict["Build-Depends-Indep"],
        normalized_global_req, control_base)

      for pack_name in section_dict["Package"].keys():
        #build_excepts[pack_name] = {}
        for dep_sect in dep_sects_list:
          section_dict["Package"][pack_name]["OnlyIf-{0}".format(dep_sect)] = dict()
          if section_dict["Package"][pack_name][dep_sect]:
            if section_dict["Package"][pack_name][dep_sect].has_key("OnlyIf"):
              section_dict["Package"][pack_name]["OnlyIf-{0}".format(dep_sect)] = \
                section_dict["Package"][pack_name][dep_sect]["OnlyIf"]
              fast_builder_tools.packages_processing(section_dict["Package"][pack_name]["OnlyIf-{0}".format(dep_sect)])
            section_dict["Package"][pack_name][dep_sect] = \
              fast_builder_tools.separate_onlyif_section(section_dict["Package"][pack_name][dep_sect])

            section_dict["Package"][pack_name]["OnlyIf-{0}".format(dep_sect)] = \
              fast_builder_tools.normalize(section_dict["Package"][pack_name]["OnlyIf-{0}".format(dep_sect)],
                base_control, control_base, control_internal, control_internal_check,
                  unknown_dep_file)
            section_dict["Package"][pack_name][dep_sect] = \
              fast_builder_tools.normalize(section_dict["Package"][pack_name][dep_sect],
                base_control, control_base, control_internal, control_internal_check,
                  unknown_dep_file)

        if section_dict["Package"][pack_name]["Main"]:
          section_dict["Package"][pack_name]["Depends"] = \
            fast_builder_tools.get_dependencies(section_dict["Package"][pack_name]["Depends"], global_req, base_control)

      loader = fast_builder_loader.Loader(main_section_list, build_dep_sects_list, dep_sects_list,
        user_defined_in_main, package_section_list, user_defined_in_packets)
      loader.load_control(control_base, base_control, section_dict)

      for sect in build_dep_sects_list:
        section_dict[sect] = fast_builder_tools.normalize(section_dict[sect],
          base_control, control_base, control_internal, control_internal_check, unknown_dep_file)
        section_dict["OnlyIf-{0}".format(sect)] = fast_builder_tools.normalize(section_dict["OnlyIf-{0}".format(sect)],
          base_control, control_base, control_internal, control_internal_check, unknown_dep_file)
        if update_if_bounds:
          for pack_name, pack_val in section_dict[sect].iteritems():
            if not pack_val:
              packs_without_bounds.add(pack_name)

      fast_builder_tools.exclude_excepts(section_dict["Build-Depends-Indep"], build_excepts)
      fast_builder_tools.exclude_excepts(section_dict["Build-Depends"], build_excepts)

      if section_dict["Update"]:
        section_dict["Build-Depends"] = fast_builder_tools.update_depends(section_dict["Build-Depends"],
          normalized_global_req, section_dict["OnlyIf-Build-Depends"].keys() +
            list(packs_without_bounds))
        section_dict["Build-Depends-Indep"] = fast_builder_tools.update_depends(section_dict["Build-Depends-Indep"],
          normalized_global_req, section_dict["OnlyIf-Build-Depends-Indep"].keys() +
            list(packs_without_bounds))

      if section_dict["SetEpoch"]:
        section_dict["Build-Depends"] = \
          fast_builder_tools.check_epoch(section_dict["Build-Depends"], epoch_dict, gerritAccount, branch)
        section_dict["Build-Depends-Indep"] = \
          fast_builder_tools.check_epoch(section_dict["Build-Depends-Indep"], epoch_dict, gerritAccount, branch)

      for sect in build_dep_sects_list:
        fast_builder_tools.synchronize_with_onlyif(section_dict, sect)
        if section_dict[sect]:
          fast_builder_tools.filter_bounds(section_dict[sect], del_bounds_list)

      packs_without_bounds.clear()

      for pack_name in section_dict["Package"].keys():
        for dep_sect in dep_sects_list:

          if section_dict["Package"][pack_name][dep_sect]:
            fast_builder_tools.synchronize_with_onlyif(section_dict["Package"][pack_name], dep_sect)
            section_dict["Package"][pack_name][dep_sect] = \
              fast_builder_tools.normalize(section_dict["Package"][pack_name][dep_sect],
                base_control, control_base, control_internal, control_internal_check, unknown_dep_file)
            fast_builder_tools.exclude_excepts(section_dict["Package"][pack_name][dep_sect], build_excepts)

            if section_dict["Update"]:

              if update_if_bounds:
                for _pack_name, _pack_val in section_dict["Package"][pack_name][dep_sect].iteritems():
                  if not _pack_val:
                    packs_without_bounds.add(_pack_name)

              if dep_sect not in not_update_dep_list:
                section_dict["Package"][pack_name][dep_sect] = \
                  fast_builder_tools.update_depends(section_dict["Package"][pack_name][dep_sect], normalized_global_req,
                    section_dict["Package"][pack_name]["OnlyIf-{0}".format(dep_sect)].keys() + \
                      list(packs_without_bounds))
                fast_builder_tools.filter_bounds(section_dict["Package"][pack_name][dep_sect], del_bounds_list)
                if section_dict["SetEpoch"]:
                  print "Epoch checking in progress..."
                  section_dict["Package"][pack_name][dep_sect] = \
                    fast_builder_tools.check_epoch(section_dict["Package"][pack_name][dep_sect],
                      epoch_dict, gerritAccount, branch)
                  print "Epoch checking is done!"

        if not section_dict["Package"][pack_name]["Architecture"]:
          section_dict["Package"][pack_name]["Architecture"] = "any"
        if not section_dict["Package"][pack_name]["Description"]:
          section_dict["Package"][pack_name]["Description"] = "<insert up to 60 chars description>\n" \
            " <insert long description, indented with spaces>"

      control_base_file.seek(0)
      base_control_file.seek(0)
      json.dump(control_base, control_base_file, indent=4, sort_keys=True, separators=(',', ':'))
      json.dump(base_control, base_control_file, indent=4, sort_keys=True, separators=(',', ':'))
      control_base_file.truncate()
      base_control_file.truncate()

      generator = fast_builder_generator.Generator(main_section_list, build_dep_sects_list,
        dep_sects_list, package_section_list)
      generator.generate_control(section_dict)
      generator.generate_rules(build_system, build_with)
      generator.generate_changelog(section_dict)

    control_base_file.close()
    base_control_file.close()
    control_internal_file.close()
    unknown_req_file.close()
    unknown_dep_file.close()
    conf.close()

  except KeyboardInterrupt:
    print '\nThe process was interrupted by the user'
    raise SystemExit

main()