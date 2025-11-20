# -*- coding: utf-8 -*-
from modules.grv import grv_navigation

for group in grv_navigation():
    print(repr(group.get("title")))
