import yaml
from os.path import join, isdir
from os import listdir
import argparse
import pdb
import lan
import require_utils
import re

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config', dest='config', help='Configuration YAML')
args = parser.parse_args()

packageName = re.compile("[a-zA-Z0-9-_.]+")
packageNameEnd = re.compile("[a-zA-Z0-9-_.]+$")
grepTemplate0 = re.compile("import [a-zA-Z0-9-_.]+")
grepTemplate1 = re.compile("from [a-zA-Z0-9-_.]+")
sectTemplate = re.compile(":.+")

dep_sects_list = ["Depends", "Build-Depends", "Build-Depends-Indep"]
section_list = ["Source", "Section", "Priority", "Maintainer",
"Build-Depends", "Build-Depends-Indep", "Standards-Version",
"Homepage", "Package", "Depends", "Description"]
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

			section_dict["Source"] = line["Source"]
			section_dict["Section"] = line["Section"]
			section_dict["Priority"] = line["Priority"]
			section_dict["Maintainer"] = line["Maintainer"]
			if line["Build-Depends"]:
				section_dict["Build-Depends"] = line["Build-Depends"]
				for el in section_dict["Build-Depends"].keys():
					section_dict["Build-Depends"][el] = set(section_dict["Build-Depends"][el].items())
			if line["Build-Depends-Indep"]:
				section_dict["Build-Depends-Indep"] = line["Build-Depends-Indep"]
				for el in section_dict["Build-Depends-Indep"].keys():
					section_dict["Build-Depends-Indep"][el] = set(section_dict["Build-Depends-Indep"][el].items())
			section_dict["Standards-Version"] = line["Standards-Version"]
			section_dict["Homepage"] = line["Homepage"]
			section_dict["Package"] = line["Package"]
			section_dict["Architecture"] = line["Architecture"]
			if line["Depends"]:
				section_dict["Depends"] = line["Depends"]
				for el in section_dict["Depends"].keys():
					section_dict["Depends"][el] = set(section_dict["Depends"][el].items())
			section_dict["Description"] = line["Description"]

			load_control()

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

			print get_dependencies(global_req, depends)
			print get_build_dependencies(global_req, build_depends)
			
			for el in section_list:
				if section_dict.has_key(el):
					print "{0}{1}".format(el, section_dict[el])

			build_control()
		conf.close()

	except KeyboardInterrupt:
		print '\nThe process was interrupted by the user'
        raise SystemExit

def get_build_dependencies(global_req, build_depends, py_file_names = ["setup.py"]):
	build_depends = dict(build_depends.items() + {"python-setuptools" : {}, "python-all" : {},
		"python-dev" : {}, "debhelper" : {(">=", "9")}}.items())

	excepts = {"python-distutils.core" : {}, "python-sys" : {}, "python-setup" : {},
		"python-argparse" : {}, "python-ordereddict" : {}}

	build_depends = dict(build_depends.items() +
		recur_search(names = py_file_names, search_type = "grep").items())

	for el in excepts:
		if build_depends.has_key(el):
			del build_depends[el]
	return build_depends

def get_dependencies(global_req, depends, req_file_names = ["requires.txt", "requirements.txt"]):
	try:
		with open(recur_search(req_file_names), 'r') as req_file:
			for line in req_file:
				req_pack = packageName.search(line)
				if req_pack:
					depends.setdefault(req_pack.group(0), global_req[req_pack.group(0)])
	except IOError:
		print "There is no requirements!"
	return depends

def recur_search(names, relative_path = ".", search_type = "default"):
	for el in listdir(relative_path):
		if isdir(join(relative_path, el)):
			path = recur_search(names, join(relative_path, el), search_type)
			if path:
				return path
		else:
			if search_type == "grep" and el in names:
				try:
					with open(join(relative_path, el),'r') as grep_file:
						res_grep = dict()
						for line in grep_file:
							imp = grepTemplate0.search(line)
							frm = grepTemplate1.search(line)
							if imp:
								res_grep.setdefault("python-" + packageNameEnd.search(imp.group(0)).group(0), {})
							if frm:
								res_grep.setdefault("python-" + packageNameEnd.search(frm.group(0)).group(0), {})
						return res_grep
				except IOError:
					None
			elif el in names:
				return join(relative_path, el)
	return None

def load_control(control_file_name = "control"):
	try:
		with open(recur_search(control_file_name), 'r') as cont_file:
			for line in cont_file:
				for el in section_dict.keys():
					if el not in dep_sects_list and el in line:
						if not section_dict[el]:
							section_dict[el] = sectTemplate.search(line).group(0)
	except IOError:
		print "There is no control file!"

def build_control(control_file_name = "control"):
	try:
		with open(recur_search(control_file_name), "w+") as control_file:
			for el in section_list:
				control_file.write(el)
				if el not in dep_sects_list:
					control_file.write(section_dict[el] + "\n")
				else:
					print el
					print section_dict[el]	
					if section_dict[el]:
						for key, val in section_dict[el].items():
							control_file.write("\n")
							for el2 in val:
								control_file.write(" {0} ({1} {2}),".format(key, el2[0], el2[1]))
					else:
						control_file.write("\n")
						control_file.write(" {0},".format(el))
	except IOError:
		print "Error while overwriting control file!"

main()