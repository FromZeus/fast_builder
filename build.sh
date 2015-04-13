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

	if [[ "${tarName}" == "" ]]
		then
			exit 1
	fi

	tarName=${tarName#./}
	packageName=$tarName
	packageName=${packageName%.tar.gz}
	packageName=${packageName,,}
	packageName=${packageName//[_]/-}

	mkdir "python-${packageName}"
	pushd "python-${packageName}"
	tar -xzvf "../${tarName}"

	buf=${tarName%.tar.gz}
	mv ${buf}/* .
	rm -rf ${buf}

	dh_make -e ${email} -f "../${tarName}" -s -y

	popd
	popd
	python builder.py -c "config.yaml" > builder.log
	pushd "package"
	pushd "python-${packageName}"

	set DEB_BUILD_OPTIONS=nocheck 
	dpkg-buildpackage -rfakeroot -us -uc
	
	popd
	deb_tar_gz=$(find . -name "*.debian.tar.gz")
	orig_tar_gz=$(find . -name "*.orig.tar.gz")
	tar -xzvf ${deb_tar_gz}
	tar -xzvf ${orig_tar_gz}
	pushd "debian"
	for i in $(find . -regextype posix-egrep -regex "*(.EX|.ex|README.debian)$"); do rm -f $i; done
	popd
	rm -rf "python-${packageName}"
	for i in $(find . -regextype posix-egrep -regex ".*(dsc|changes|debian.tar.gz|orig.tar.gz)$"); do rm -f $i; done
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