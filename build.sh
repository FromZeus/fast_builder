#!/bin/bash

#set -x

except()
{
	case "$1" in
		-e)
			echo "-e There have to be e-mail address: example@example.com"
			exit 1
			;;
	esac
}

main()
{
	pushd "package"
	tarName=$(find . -name "*.tar.gz")
	tarName=${tarName#./}
	packageName=$tarName
	if [ "${packageName}" = "" ]
		then
			echo "No package in the directory"
			exit 1
	fi

	packageName=${packageName%.tar.gz}
	packageName=${packageName,,}

	mkdir "python-${packageName}"
	pushd "python-${packageName}"
	tar -xvf "../${tarName}"

	buf=${tarName%.tar.gz}
	mv ${buf}/* .
	rm -rf ${buf%.tar.gz}

	dh_make -e ${email} -f "../${tarName}" -s -y

	popd
	popd
	python builder.py -c "config.yaml"
	pushd "package"
	pushd "python-${packageName}"

	set DEB_BUILD_OPTIONS=nocheck 
	dpkg-buildpackage -rfakeroot -us -uc

	popd
	deb_tar_gz=$(find . -name "*.debian.tar.gz")
	orig_tar_gz=$(find . -name "*.orig.tar.gz")
	tar -xvf ${deb_tar_gz}
	tar -xvf ${orig_tar_gz}
	pushd "debian"
	for i in $(find . . -regextype posix-egrep -regex ".*(EX|ex)$"); do rm -f $i; done
	popd
	#tar -cvf ${deb_tar_gz} "debian"
	#rm -rf "debian"

}

if [ $# -eq 0 ]
	then
		echo "Please, specify arguments"
		exit 1
fi

while [ $# -gt 0 ]
do
	case "$1" in
		-e)
			shift
			if [ $# -gt 0 ]
				then
					email="$1"
				else
					except -e
			fi
			shift
			;;
		*)
			shift
			;;
	esac
done

$(main)