import fast_builder_tools
import operator
import re
import subprocess

class Generator:

  main_section_list = []
  build_dep_sects_list = []
  dep_sects_list = []
  package_section_list = []
  cap_of_changelog = re.compile("[a-zA-Z0-9-_.]+\s*\((\d[.]*[a-z:]*)+(\d[.]*[a-z+-~:]*)*\)" \
    "\s*[a-zA-Z0-9-_.]+\s*;\s*urgency=[a-z]+")
  packageName = re.compile("([a-zA-Z0-9-_.]+|(\$\{[^\s]*\})+)")
  packageVersChangelog = re.compile("(\d[.a-z:]*)+")
  pacakgeRevis = re.compile("[0-9.a-z+-~:]+\s*\)")

  def __init__(self,
    main_section_list,
    build_dep_sects_list,
    dep_sects_list,
    package_section_list):
    self.main_section_list = main_section_list
    self.build_dep_sects_list = build_dep_sects_list
    self.package_section_list = package_section_list
    self.dep_sects_list = dep_sects_list

  def generate_out_pack(self, pack_name, pack_val):
    if pack_name:
      if pack_val:
        for dep_el in pack_val:
          if dep_el[0] == "!=":
            out_pack = " {0} (<< {1}) | {0} (>> {1})," \
              .format(pack_name, dep_el[1])
          else:
            out_pack = " {0} ({1} {2})," \
              .format(pack_name, dep_el[0], dep_el[1])
      else:
        out_pack = " {0},".format(pack_name)
    return out_pack

  def generate_control(self, section_dict, control_file_name = "control"):

    def write_packs(sect):
      for pack_name, pack_val in sorted(sect.items(), key = operator.itemgetter(0)):
        control_file.write(self.generate_out_pack(pack_name, pack_val))
        control_file.write("\n")

    try:
      with open(fast_builder_tools.recur_search(control_file_name), "w+") as control_file:
        for main_sect in self.main_section_list:
          if section_dict[main_sect] and section_dict.has_key(main_sect):
            if main_sect in self.build_dep_sects_list:
              control_file.write("{0}:\n".format(main_sect))
              write_packs(section_dict[main_sect])
            else:
              control_file.write("{0}: {1}\n".format(main_sect, section_dict[main_sect]))
        for pack, value in section_dict["Package"].iteritems():
          control_file.write("\nPackage: {0}\n".format(pack))
          for pack_sect in self.package_section_list:
            if value[pack_sect]:
              if pack_sect in self.dep_sects_list:
                control_file.write("{0}:\n".format(pack_sect))
                write_packs(value[pack_sect])
              else:
                control_file.write("{0}: {1}\n".format(pack_sect, value[pack_sect]))
    except (IOError, TypeError):
      print "Error while overwriting control file!"

  def generate_rules(self, build_system, build_with, rules_file_name = "rules"):
    try:
      content = []
      with open(fast_builder_tools.recur_search(rules_file_name), "r") as rules_file:
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

      with open(fast_builder_tools.recur_search(rules_file_name), "w+") as rules_file:
        rules_file.writelines(content)

    except (IOError, TypeError):
      print "Error while overwriting rules file!"

  def generate_changelog(self, section_dict, changelog_file_name = "changelog"):
    try:
      content = []
      cap_flag = False
      with open(fast_builder_tools.recur_search(changelog_file_name), "r") as changelog_file:
        for line in changelog_file.readlines():
          cap = self.cap_of_changelog.search(line)
          if cap and not cap_flag:
            cap_flag = True
            cap_line = cap.group(0)
            pack_name = self.packageName.search(cap_line)
            pack_name = pack_name.group(0)
            if not section_dict["PakageName"]:
              section_dict["PakageName"] = pack_name

            cap_line = cap_line[len(pack_name):]
            pack_ver_idx = [(it.start(), it.end()) for it in
              self.packageVersChangelog.finditer(cap_line)]
            pack_ver = cap_line[pack_ver_idx[0][0]:pack_ver_idx[0][1]]
            if not section_dict["Version"]:
              section_dict["Version"] = pack_ver

            cap_line = cap_line[pack_ver_idx[0][1]:]
            pack_revis_idx = [(it.start(), it.end()) for it in
              self.pacakgeRevis.finditer(cap_line)]
            if not pack_revis_idx:
              pack_revis_idx = pack_ver_idx
              pack_revis = ""
            else:
              pack_revis = cap_line[pack_revis_idx[0][0]:pack_revis_idx[0][1]]
              pack_revis = re.sub("\s*\)", "", pack_revis)
              cap_line = cap_line[pack_revis_idx[0][1]:]
            if not section_dict["Revision"]["Main"]:
              section_dict["Revision"]["Main"] = pack_revis

            pack_tag_idx = [(it.start(), it.end()) for it in
              self.packageName.finditer(cap_line)]
            pack_tag = cap_line[pack_tag_idx[0][0]:pack_tag_idx[0][1]]
            if not section_dict["Tag"]:
              section_dict["Tag"] = pack_tag

            cap_line = cap_line[pack_tag_idx[0][1]:]
            pack_urgency_idx = [(it.start(), it.end()) for it in
              re.finditer("urgency", cap_line)]
            pack_urgency = re.search("[a-z]+", cap_line[pack_urgency_idx[0][1]:])
            pack_urgency = pack_urgency.group(0)
            if not section_dict["Urgency"]:
              section_dict["Urgency"] = pack_urgency
          content.append(line)

        content.insert(0, " -- {0}  {1}\n".format(section_dict["Maintainer"], subprocess.check_output("date -R", shell=True)))
        content.insert(0, "  * Generated by FastBuilder\n\n")
        content.insert(0, "{0} ({1}{2}) {3}; urgency={4}\n\n".format(section_dict["PakageName"],
          section_dict["Version"], section_dict["Revision"]["Main"] + fast_builder_tools.none_check(section_dict["Revision"]["Append"]),
          section_dict["Tag"], section_dict["Urgency"]))

      with open(fast_builder_tools.recur_search(changelog_file_name), "w+") as changelog_file:
        changelog_file.writelines(content)

    except (IOError, TypeError):
      print "Error while overwriting changelog file!"