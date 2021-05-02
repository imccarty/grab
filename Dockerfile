FROM ubuntu:latest

# Set the tiemzone in the image
ENV TZ=America/Los_Angeles
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt update && apt install -y gpg curl python3 && apt clean
RUN echo 'deb http://download.opensuse.org/repositories/home:/m-grant-prg/Debian_10/ /' | tee /etc/apt/sources.list.d/home:m-grant-prg.list \
    && curl -fsSL https://download.opensuse.org/repositories/home:m-grant-prg/Debian_10/Release.key | gpg --dearmor | tee /etc/apt/trusted.gpg.d/home:m-grant-prg.gpg > /dev/null \
    && apt update && apt install -y get-iplayer && apt clean

WORKDIR /app
RUN mkdir -p $HOME/transfer && mkdir -p $HOME/downloads && get_iplayer --prefs-add --output="$HOME/downloads"
COPY grab.py grab.py

#VOLUME ["$HOME/.get_iplayer", "$HOME/transfer"]

ENTRYPOINT [ "python3", "grab.py" ]
