FROM ubuntu
RUN apt-get update && apt-get -y install build-essential gawk git libncurses5-dev time wget python python3-pip zlib1g-dev fish unzip vim && pip3 install tornado terminado
RUN useradd builduser -s /usr/bin/fish && mkdir /home/builduser && mkdir /home/builduser/worker && chown -R builduser:builduser /home/builduser
USER builduser
RUN cd && git clone https://github.com/openwrt/openwrt
RUN cd ~/openwrt && ./scripts/feeds update -a && ./scripts/feeds install -a && mkdir package/extra && make defconfig
RUN cd ~/openwrt && git config --global user.name builduser && git config --global user.email builduser@ledeforge.org && touch .customizations && git add .customizations && git commit -a -m "Customizations"
COPY worker /home/builduser/worker

EXPOSE 8765
CMD ["fish", "-c", "cd ~/worker; and python3 worker.py /home/builduser/openwrt"]
