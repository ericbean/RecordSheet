/*
Copyright (C) 2015 Eric Beanland <eric.beanland@gmail.com>

This file is part of RecordSheet

RecordSheet is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

RecordSheet is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

// baseUrl provides a prefix for urls, without requiring the app to be
// at any specfic location
var baseUrl = document.querySelector('meta[name="app-root"]').getAttribute('content');

function Post(data) {
    this.memo = ko.observable(data.memo || "");
    this.account_id = ko.observable(data.account || "");
    this.amount = ko.observable(data.amount || "");
    this.id = data.id || null;
};

/*****************************************************************************/
var _accounts = [];
var pending = null;
//retrieve a list of all accounts
function getAccounts(callback) {
    this.load_cb = function(event) {
        var xhr = event.currentTarget;
        if (xhr.status === 200) {
            var arr = JSON.parse(xhr.response).accounts
            _accounts.push(...arr);
            callback(_accounts);
        }
    };

    this.error_cb = function(event) {
        console.log("failed to retrieve accounts");
    };

    if (_accounts.length > 0) {
        callback(_accounts);
        return;
    } else if (pending) {
        pending.addEventListener("load", self.load_cb);
        return;
    }

    var oReq = new XMLHttpRequest();
    pending = oReq;
    oReq.open("GET", baseUrl+'/json/accounts?sort=name.asc');
    oReq.addEventListener("load", self.load_cb);
    oReq.addEventListener("error", self.error_cb);
    oReq.send();
};

function findAcct(name) {
    for (var acct of _accounts) {
        if (acct.name.startsWith(name)) {
            return acct;
        }
    }
    return null;
}

function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

/*****************************************************************************/
//json helpers
function cleaner(key, value) {
    if (key.startsWith("_")) {
        return;
    }
    return value;
}

function cleanJson(obj) {
    return ko.toJSON(obj, cleaner);
}

/*****************************************************************************/
// Format localize iso datetime strings
ko.bindingHandlers.DateTime = {
    init: function(element, valueAccessor, allBindings) {
        //pass
    },
    update: function(element, valueAccessor, allBindings) {
        var value = ko.unwrap(valueAccessor());
        if (value) {
            if (typeof value == 'string') { value = new Date(value); }
            if (element.tagName === "INPUT") {
                var dstr = value.toISOString();
                element.value = dstr.substring(0, dstr.length - 1);
            } else {
                element.textContent = value.toLocaleString();
            }
        }
    }
};

// Auto complete account names
ko.bindingHandlers.autoAcct = {
    init: function(element, valueAccessor, allBindings, viewModel, bindingContext) {
        element.dataset.prevText = ''; // initialized outside the event callback
        // set the inital state of element
        var acct_name = "";
        acct_name = ko.unwrap(valueAccessor());
        //convert numeric acct id to name
        if (typeof acct_name === 'number' || acct_name instanceof Number) {
            for (var acct of _accounts) {
                if (acct.id === acct_name) {
                    acct_name = acct.name;
                    break;
                }
            }
        }
        element.value = acct_name;

        ko.utils.registerEventHandler(element, 'input', function(event) {
            searchString = element.value.toUpperCase();
            acct = findAcct(searchString);
            if (element.dataset.prevText.startsWith(searchString)) {
                acct = null;
            }
            if (acct) {
                element.value = acct.name;
                if (ko.isObservable(valueAccessor())) {
                    valueAccessor()(acct.name);
                } else {
                    // quick fix but I hate this
                    bindingContext.$rawData.account_id = acct.name;
                }
                selectStart = searchString.length;
                selectEnd = acct.name.length;
                element.setSelectionRange(selectStart, selectEnd);
            } else {
                element.value = searchString;
                if (ko.isObservable(valueAccessor())) {
                    valueAccessor()(searchString);
                } else {
                    bindingContext.$rawData.account_id = searchString;
                }
            }
            element.dataset.prevText = searchString;
        }, false);
    }
};

/*****************************************************************************/

function createAcctViewModel(params) {
    var self = this;
    self._errorMsg = ko.observable("");
    self.name = ko.observable("");
    self.desc = ko.observable("");
    self.callback = params.callback || function() {};
    self.sendAcct = function() {
        self._errorMsg("");
        this.load_cb = function(event) {
            var xhr = event.currentTarget;
            var data = JSON.parse(xhr.response);
            if (xhr.status === 200) {
                _accounts.push(data);
                self.callback(data);
                self.name("");
                self.desc("");
            } else {
                self._errorMsg(data.errorMsg);
            }
        };
        this.error_cb = function(event) {
            self._errorMsg("xhr error");
        };
        var oReq = new XMLHttpRequest();
        oReq.open("PUT", baseUrl+'/json/accounts');
        oReq.addEventListener("load", self.load_cb);
        oReq.addEventListener("error", self.error_cb);
        oReq.setRequestHeader("Accept", 'application/json');
        oReq.setRequestHeader("Content-Type", 'application/json');
        oReq.setRequestHeader("X-csrf-token", getCsrfToken());
        oReq.send(cleanJson(self));
    };
}
ko.components.register('create-acct', {
    viewModel: createAcctViewModel,
    template: { rs: 'create-acct.html' }
});

/*****************************************************************************/

function createTrViewModel(params) {
    var self = this;
    self.datetime = ko.observable();
    self.memo = ko.observable("");
    self.posts = params.posts;
    self.dateEditible = params.dateEditible || false;
    if (!self.dateEditible) {
        self.datetime(new Date());
    }
    self.errorMsg = ko.observable("");
    self.sendPosts = function() {
        if (!self.memo()) {
            self.errorMsg("Bad memo");
            return;
        }
        if (self.posts().length < 2) {
            self.errorMsg("Must have at least 2 posts");
            return;
        }
        var o = {
            datetime: self.datetime(),
            memo: self.memo(),
            posts: self.posts()
        }
        this.load_cb = function(event) {
            var xhr = event.currentTarget;
            var jsonData = JSON.parse(xhr.response)
            if (xhr.status === 200) {
                for (let post of self.posts()) {
                    post.posted = true;
                }
                self.posts.removeAll();
                self.errorMsg("");
            } else {
                self.errorMsg(jsonData.errorMsg);
            }
        };
        this.error_cb = function(event) {
            console.log("xhr error");
            console.log(event);
        };
        var oReq = new XMLHttpRequest();
        oReq.open("PUT", baseUrl+'/json/journal');
        oReq.addEventListener("load", self.load_cb);
        oReq.addEventListener("error", self.error_cb);
        oReq.setRequestHeader("Accept", 'application/json');
        oReq.setRequestHeader("Content-Type", 'application/json');
        oReq.setRequestHeader("X-csrf-token", getCsrfToken());
        oReq.send(cleanJson(o));
    };
    self.addRow = function() {
        var p = new Post({amount:-self.sum()});
        self.posts.push(p);
    };
    self.removePost = function(post) {
        self.posts.remove(post);
    };
    self.posts.subscribe(function(changes) {
        changes.forEach(function(change) {
            if (change.status === 'added' && self.posts().length === 1) {
                p = change.value;
                self.datetime(p.datetime || new Date());
                self.memo(ko.unwrap(p.memo));
            } else if (change.status === 'deleted') {
                if (self.posts().length === 0) {
                    self.datetime(new Date());
                    self.memo("");
                } else {
                    p = self.posts()[0];
                    self.datetime(p.datetime);
                    self.memo(ko.unwrap(p.memo));
                }
            }
        });

    }, null, "arrayChange");
    self.sum = function() {
        //multiply and divide by 100,000,000 to overcome floating point imprecision
        var multiplier = 100000000 // big enough to handle bitcoin decimals
        var sum = 0;
        for (let post of self.posts()) {
            sum += (Number(post.amount) * multiplier)
        }
        return sum / multiplier;
    }
};
ko.components.register('create-tr', {
    viewModel: createTrViewModel,
    template: {rs:'create-tr.html'}
});

/*****************************************************************************/
//templating system
function GetRsComponent(url, callback) {
    url = '/static/html/' + url;
    this.load_cb = function(event) {
        var xhr = event.currentTarget;
        if (xhr.status === 200) {
            callback(xhr.response);
        }
    };
    this.error_cb = function(event) {
        console.log("xhr error");
        console.log(event);
    };
    var oReq = new XMLHttpRequest();
    oReq.open("GET", baseUrl+url);
    oReq.addEventListener("load", self.load_cb);
    oReq.addEventListener("error", self.error_cb);
    oReq.send();
};

var rsComponentLoader = {
    loadTemplate: function(name, templateConfig, callback) {
        if (templateConfig.rs) {
            GetRsComponent(templateConfig.rs, function(data) {
                ko.components.defaultLoader.loadTemplate(name, data, callback);
            });
        } else {
            callback(null);
        }
    }
};
ko.components.loaders.unshift(rsComponentLoader);
/*****************************************************************************/

