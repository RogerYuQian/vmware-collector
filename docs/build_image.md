# Build image

You can build the image by using kolla's build.py script.

    # prepare code
    mkdir ~/extra_docker
    cd ~/extra_docker
    git clone http://gitlab.sh.99cloud.net/99cloud/vmware_collector.git


    # go to kolla folder
    cd <kolla>
    ./tools/build.py --docker-dir ~/extra_docker ^vmware_collector

Then you will get images

