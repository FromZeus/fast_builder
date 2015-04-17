import re

package_with_version = \
	re.compile("(\d*[a-zA-Z-_.]\d*)+\s*(\((\s*(>>|<<|=|>=|<=)+\s*(\d[.]*)+\s*)" \
		"(\|{1}\s*(>>|<<|=|>=|<=)+\s*(\d[.]*)+\s*){,1}\)){,1}")
packageName = re.compile("(\d*[a-zA-Z-_.]\d*)+")
packageEq = re.compile("(>=|<=|>>|<<|==)+")
packageVers = re.compile("(\d[.]*)+")

line = "pbr (>= 0.10), posix_ipc (<< 0.5 | >> 0.5), albemic (<< 1.3)," \
"\n heatclient (>> 0.3.1) \n ,barbican (>= 0.5), barbican(<< 1.0 | >> 1.0)"

entry_list = [it.start() for it in package_with_version.finditer(line)]
print entry_list

for el in entry_list:
	pack = package_with_version.search(line[el:]).group(0)
	print "{0} {1} {2}".format(packageName.search(pack).group(0),
		packageEq.search(pack).group(0), packageVers.search(pack).group(0))