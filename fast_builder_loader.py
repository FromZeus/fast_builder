import fast_builder_tools
import re

class Loader:

  dep_sects_list = []
  build_dep_sects_list = []
  main_section_list = []
  user_defined_in_main = []
  build_dep_sects_list = []
  package_section_list = []
  user_defined_in_packets = []
  sectTemplate = re.compile(":.+")

  def __init__(self,
    main_section_list,
    build_dep_sects_list,
    dep_sects_list,
    user_defined_in_main,
    package_section_list,
    user_defined_in_packets):
    self.main_section_list = main_section_list
    self.build_dep_sects_list = build_dep_sects_list
    self.dep_sects_list = dep_sects_list
    self.user_defined_in_main = user_defined_in_main
    self.package_section_list = package_section_list
    self.user_defined_in_packets = user_defined_in_packets

  def load_control(self, control_base, base_control, section_dict, control_file_name = "control"):

    def add_to_dep_sect(cur_sect, section_in_dict, line):
      packs_in_line = fast_builder_tools.parse_packages(line)
      if not section_in_dict[cur_sect]:
        section_in_dict[cur_sect] = dict()
      for pack_name, pack_val in packs_in_line.iteritems():
        section_in_dict[cur_sect].setdefault(pack_name, pack_val)
        section_in_dict[cur_sect][pack_name] |= pack_val

    def add_to_sect(cur_sect, section_in_dict, line):
      sect_templ_line = self.sectTemplate.search(line)
      new_line = ""
      if sect_templ_line:
        new_line = re.sub(":\s+", "", sect_templ_line.group(0))
      elif line.startswith(" "):
        new_line = line
      section_in_dict[cur_sect] = (section_in_dict[cur_sect] +
        "\n{0}".format(new_line.rstrip()) if section_in_dict[cur_sect] else new_line)

    try:
      with open(fast_builder_tools.recur_search(control_file_name), 'r') as control_file:
        cur_package = cur_sect = packages = ""
        for line in control_file:
          if line.startswith("#") or line == "\n":
            continue
          if "Package:" in line:
            cur_package = re.sub(":\s+", "",
              self.sectTemplate.search(line).group(0))
            if not fast_builder_tools.check_in_base(control_base, cur_package):
              control_base[cur_package] = cur_package
            if not fast_builder_tools.check_in_base(base_control, cur_package):
              base_control[cur_package] = cur_package
            continue
          if not cur_package:
            for package_sect in self.main_section_list:
              if "{0}:".format(package_sect) in line:
                if cur_sect in self.build_dep_sects_list:
                  add_to_dep_sect(cur_sect, section_dict, packages + ",")
                packages = ""
                cur_sect = package_sect
                break
            if cur_sect not in self.user_defined_in_main:
              if cur_sect in self.build_dep_sects_list:
                packages += line.rstrip()
              else:
                add_to_sect(cur_sect, section_dict, line)
          else:
            for package_sect in self.package_section_list:
              if "{0}:".format(package_sect) in line:
                if cur_sect in self.dep_sects_list:
                  add_to_dep_sect(cur_sect, section_dict["Package"][cur_package], packages + ",")
                packages = ""
                cur_sect = package_sect
                break
            if cur_sect not in self.user_defined_in_packets[cur_package]:
              if cur_sect in self.dep_sects_list:
                packages += line.rstrip()
              else:
                add_to_sect(cur_sect, section_dict["Package"][cur_package], line)

    except (IOError, TypeError):
      print "There is no control file!"