.PHONY: all install uninstall clean distclean

PREFIX := /usr
bindir := $(PREFIX)/bin
datarootdir := $(PREFIX)/share

program_unix_name := pydeposits
data_dir := $(datarootdir)/$(program_unix_name)

all:

install: all
	for file in $$(find pycl pydeposits -name '*.py'); do \
		install -m 0644 -D $$file $(DESTDIR)$(data_dir)/$$file; \
	done
	mkdir -p $(DESTDIR)$(bindir)
	echo '#!/bin/sh\nPYTHONPATH=$(data_dir) exec $(data_dir)/$(program_unix_name)/main.py "$$@"' > $(DESTDIR)$(bindir)/$(program_unix_name)
	chmod a+x $(DESTDIR)$(data_dir)/$(program_unix_name)/main.py
	chmod a+x $(DESTDIR)$(bindir)/$(program_unix_name)

uninstall:
	for file in $$(find pycl pydeposits -name '*.py'); do \
		rm -f $(DESTDIR)$(data_dir)/$$file; \
	done
	for dir in $$(find $(DESTDIR)$(data_dir) -type d | sort -r); do \
		rmdir --ignore-fail-on-non-empty $$dir; \
	done
	rm -f $(DESTDIR)$(bindir)/$(program_unix_name)

clean:
distclean: clean

