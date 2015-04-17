import re

package_with_version = \
	re.compile("(\d*[a-zA-Z-_.]\d*)+\s*(\((\s*(>>|<<|=|>=|<=)+\s*(\d[.]*)+\s*)" \
		"(\|{1}\s*(>>|<<|=|>=|<=)+\s*(\d[.]*)+\s*){,1}\)){,1},")

print package_with_version.findall("pbr (>= 0.10), posix_ipc (<< 0.5 | >> 0.5),")

entry_list = [it.start() for it in package_with_version.finditer("pbr (>= 0.10), posix_ipc (<< 0.5 | >> 0.5),")]
print entry_list