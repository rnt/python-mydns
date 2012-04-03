mydns.py
========

Author: Milan Nikolic 
License: GPL-3

### Using

    Usage: mydns.py <options> <args>

    Examples:
    mydns.py --aux 10 --type A --name www example.com list_of_domains.txt --update
    mydns.py --type A,MX example.com --delete-rr --pretend
    mydns.py --list | grep "^exa" | mydns.py --deactivate
    mydns.py --create-bundle --data 192.168.1.100 --bundle-ns "ns1.example.com,ns2.examplecom" list_of_domains.txt

    Options:
      -h, --help            show this help message and exit
      --ns=NS               the name of the name server. (default
                            ns1.newnameserver.com.)
      --mbox=MBOX           mailbox of the person responsible for this zone.
                            (default hostmaster.newnameserver.com.)
      --refresh=REFRESH     the number of seconds after which slave nameservers
                            should check to see if this zone has been changed.
                            (default 43200)
      --retry=RETRY         the number of seconds a slave nameserver should wait
                            before retrying if it attempts to transfer this zone
                            but fails. (default 1800)
      --expire=EXPIRE       if for expire seconds the primary server cannot be
                            reached, all information about the zone is invalidated
                            on the secondary servers. (default 2419200)
      --minimum=MINIMUM     the minimum TTL field that should be exported with any
                            RR from this zone. (default 10800)
      --ttl=TTL             the number of seconds that this zone may be cached
                            before the source of the information should again be
                            consulted. (default 86400)
      --xfer=XFER           IP addresses separated by commas that will be allowed
                            to transfer the zone. (default 66.154.20.131)
      --name=NAME           the name that describes RR. (ex: www)
      --type=TYPE           DNS record types, separated by commas.
                            (A,AAAA,CNAME,HINFO,MX,NAPTR,NS,PTR,RP,SRV,TXT)
      --data=DATA           the data associated with resource record.
      --aux=AUX             An auxillary numeric value in addition to data. For
                            `MX' records, this field specifies the preference. For
                            `SRV' records, this field specifies the priority.
      --rr-ttl=RR_TTL       the number of seconds that resource record may be
                            cached before the source of the information should
                            again be consulted. (default 87600)
      --activate            activate soa record
      --deactivate          deactivate soa record
      --list                list all origins
      --pretend             perform a dry run with no changes made (used with
                            create/update/delete)
      --update              update soa and rr records
      --create              create soa record
      --create-rr           create rr records
      --delete              delete soa and all associated rr records
      --delete-rr           delete rr records
      --create-bundle       creates bundle (creates *,mail,www A records and also
                            NS and MX records)
      --bundle-ns=BUNDLE_NS
                            bundle name servers, separated by commas.
