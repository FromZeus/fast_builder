import re

build_depends = re.compile('"[a-zA-Z0-9-_.|<|>|=|!]+"')

requirements = []
with open('package/setup.py', 'r') as parsing_file:
    for line in parsing_file:
        req_pack = build_depends.search(line)
        if req_pack:
            req_pack_name = req_pack.group(0)[1:-1:]

            if len(req_pack_name) <= 1 \
                    or req_pack_name in requirements\
                    or req_pack_name.startswith('__')\
                    or req_pack_name.endswith('.py')\
                    or req_pack_name.endswith('.rst'):
                continue
            else:
                requirements.append(req_pack_name)


for i in requirements:
    print i