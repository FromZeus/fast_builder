#!/bin/bash

#set -x

bold=`tput bold`
normal=`tput sgr0`
in_stages=()

except()
{
  case "$1" in
    -e)
      echo "-e There have to be e-mail address: example@example.com"
      exit 1
      ;;
    -s)
      echo "-s Stages are not specified"
      exit 1
      ;;
  esac
}

usage()
{
  echo -e "Usage: $0 [<parameter>] <value>
Parameters:
 -h\tHelp
 -e\t<example@example.com> e-mail which will be used as maintainer e-mail in control file.
 -s\t<1|2|3> Stages of building. You can specify any combination of this three stages."
 exit 0
}


check_in_array()
{
  for el in "${@:2}"
    do
      [[ "$1" == "${el}" ]] && echo "1" && return 0
    done
  echo "0"
  return 1
}

main()
{
  pushd "package"
  tarName=$(find . -regex ".*/.*[^\(orig\|debian\)].tar.gz")

  if [[ "${tarName}" == "" ]]; then
    echo "There is no .tar.gz! You can't execute 1 and 3 stages."
    in_stages=( ${in_stages[@]/[13]/} )
  fi

  tarName=${tarName#./}
  packageName=$tarName
  packageName=${packageName%.tar.gz}
  packageName=${packageName,,}
  packageName=${packageName//[_]/-}

  if echo "$packageName" | grep -q "python-"; then
    dirName="${packageName}"
  else
    dirName="python-${packageName}"
  fi

  popd

  if [[ $(find ./package/* -type d -name "*") == "" ]]; then

    if [[ "${tarName}" == "" ]]; then
      echo "Nothing to do here"
      exit 0
    fi
    
    pushd "package"
    mkdir "${dirName}"
    pushd "${dirName}"
    tar -xzvf "../${tarName}"
    
    buf=${tarName%.tar.gz}
    mv ${buf}/* .
    rm -rf ${buf}
    popd
    popd
  fi

  if [[ "$(check_in_array 1 ${in_stages[@]})" == "1" ]]; then
    pushd "package"
    pushd "${dirName}"

    dh_make -e ${email} -f "../${tarName}" -s -y

    popd
    popd
  fi

  if [[ "$(check_in_array 2 ${in_stages[@]})" == "1" ]]; then
    echo "${bold}"
    python builder.py -c "config.yaml" | tee builder.log
    echo "${normal}"
  fi

  if [[ "$(check_in_array 3 ${in_stages[@]})" == "1" ]]; then
    pushd "package"
    pushd "${dirName}"
    
    set DEB_BUILD_OPTIONS=nocheck
    dpkg-buildpackage -rfakeroot -us -uc
    
    popd
    deb_tar_gz=$(find . -name "*.debian.tar.gz")
    orig_tar_gz=$(find . -name "*.orig.tar.gz")
    tar -xzvf ${deb_tar_gz}
    tar -xzvf ${orig_tar_gz}
    pushd "debian"
    for i in $(find . -regextype posix-egrep -regex ".*(EX|ex|README.Debian)$"); do rm -f $i; done
    popd
    rm -rf "${dirName}"
    for i in $(find . -regextype posix-egrep -regex ".*(dsc|changes|debian.tar.gz|orig.tar.gz)$")
      do rm -f $i; done
  fi
  echo "${bold}Done!${normal}"
}

if [ $# -eq 0 ]; then
  echo "Please, specify arguments"
  exit 1
fi

while [ $# -gt 0 ]
do
  case "$1" in
    -e)
      shift
      if [ $# -gt 0 ]; then
        email="$1"
      else
        except -e
      fi
      shift
      ;;
    -s)
      shift
      if [ $# -gt 0 ]; then
        in_stages+=("$@")
      else
        except -s
      fi
      ;;
    -h)
      usage
      shift
      ;;
    *)
      shift
      ;;
  esac
done

main