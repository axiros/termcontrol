#!/bin/bash

rm -f success
d="$(pwd)"


function main { 

    test "$1" == "start" && {
        echo $$ > testpid
        xterm -l -e "$0" &
        sleep 1
        tail -f Xterm.log*
        exit 0
    }
    
    pytest -xs . && touch "$d/success"
    kill $(cat "$d/testpid") 

}

main "$@"

