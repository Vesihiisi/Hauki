$(document).ready(function() {

    var sandbox = "L123"

    $(".filter-bar-check").attr("autocomplete", "off");

    function runLocally() {
        if (location.hostname == "localhost" || location.hostname == "127.0.0.1") {
            return true
        } else {
            return false
        }
    }

    function getParamValue(param) {
        var url_string = window.location.href
        var url = new URL(url_string);
        return url.searchParams.get(param);
    }


    function getSelectedLanguage() {
        return $("#language-selector option:selected").attr('data-code')
    }

    function getSearchQuery() {
        return $("#lexeme-searchbox").val()
    }

    function getToken(formElement) {
        var thisForm = $(formElement.closest("form"))
        var token = thisForm.children('input[name="csrf_token"]')
        return token.val()
    }


    function executeSearch() {
        language = getSelectedLanguage()
        query = getSearchQuery()
        url = $SCRIPT_ROOT + "/lex/" + language + "/" + query
        window.open(url, "_self")
    }

    var engine = new Bloodhound({
        remote: {
            url: $SCRIPT_ROOT + '/autocomplete',
            wildcard: '*',
            limit: 20,
            prepare: function(query, settings) {
                settings.url += '?query=' + query + "&lang=" + getSelectedLanguage();
                return settings;
            },
            transform: function(response) {
                return response;
            }
        },
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        datumTokenizer: Bloodhound.tokenizers.whitespace,
    });

    $(".filter-bar-check").click(function() {
        if (runLocally()) {
            var url = "http://127.0.0.1:5000" + window.location.pathname
        } else {
            var url = "http://" + window.location.hostname + window.location.pathname
        }
        var filterButton = $("#filter-button")
        var withSenses = $("#with-senses").is(":checked")
        var withoutSenses = $("#without-senses").is(":checked")
        var senses
        var newUrl = url
        if (!withSenses && !withoutSenses) {
            filterButton.removeAttr("href");
            return
        } else if (withSenses && !withoutSenses) {
            senses = "true"
        } else if (!withSenses && withoutSenses) {
            senses = "false"
        }
        if (senses) {
            newUrl = newUrl + "?sense=" + senses
        }
        filterButton.attr("href", newUrl)
    })

    $('#lexeme-searchbox').typeahead(null, {
        name: 'my-dataset',
        source: engine,
        limit: 12
    });

    $("#search-button").click(function() {
        if ($("#lexeme-searchbox").val()) {
            executeSearch()
        }
    });

    $("#lexeme-searchbox").keypress(function(e) {
        if (e.which == 13 && $(this).val()) {
            $('#search-button').click();
        }
    });

    $('#lexeme-searchbox').on('typeahead:selected', function(evt, item) {
        executeSearch()
    })

    function createSenseInput() {
        var field = $('<input>', {
            "class": "addSenseField",
        }).attr('type', 'text');
        field.keypress(function(e) {
            if (e.which == 13 && $(this).val()) {
                e.preventDefault()
                $('.add-sense-button').click();
            }
        });
        return field
    }

    function createAlert(type, message) {
        return $(
            '<div class="alert alert-' + type + ' alert-dismissible \
            fade show">' + message + '<button type="button" \
            class="close" data-dismiss="alert" \
            aria-label="Close"><span aria-hidden="true">\
            &times;</span></button></div>');
    }

    $(".addLexemeField").keypress(function(e) {
        if (e.which == 13 && $(this).val()) {
            e.preventDefault()
            $('.add-lexeme-button').click();
        }
    });

    $(".addLexemeField").on('input', function() {
        var thisForm = $(this).parent('form');
        var lemma = $(this).val();
        var lang = $("#lang-selector option:selected").attr('data-lang');
        $(".alert").remove();
        if (lemma.length > 1) {
            url = $SCRIPT_ROOT + '/get_duplicates/' + lang + "/" + lemma,
                $.ajax({
                    url: url,
                    type: 'GET',
                    success: function(data) {
                        if (data) {
                            $(".alert").remove();
                            data = JSON.parse(data)
                            var info = "<strong><a href='" + $SCRIPT_ROOT + "/lex/" + lang + "/" + data[0]["label"] + "'>" + data[0]["label"] + "</a></strong> already exists: "

                            for (i = 0; i < data.length; ++i) {
                                info = info + "[<a href='" + data[i].uri + "' target=_blank>" + data[i].id + "</a>] "
                            }
                            var infoMessage = createAlert("info", info);
                            thisForm.after(infoMessage);

                        }
                    }
                });
        }

    });


    $('.add-lexeme-button').click(function() {
        var lastAddedList = $("#recently-created-list");
        var addLexemeButton = $(this);
        var addLexemeField = $(".addLexemeField");
        var thisForm = $(this).parent('form');
        var newLemma = addLexemeField.val().trim();
        var pos = $("#pos-selector option:selected").attr('data-code')
        var lang = $("#lang-selector option:selected").attr('data-lang')
        if (newLemma.length > 1) {
            lex_data = JSON.stringify({
                "what": "new",
                "lang": lang,
                "content": newLemma,
                "pos": pos,
                "lid": null,
                "token": getToken($(this))
            })
            $.ajax({
                url: $SCRIPT_ROOT + '/edit',
                dataType: 'json',
                type: 'post',
                contentType: 'application/json',
                data: lex_data,
                success: function(data) {
                    l_id = data["entity"]["id"];
                    lastAddedList.prepend("<li><a href='https://www.wikidata.org/wiki/Lexeme:" + l_id + "' \
                            target='_blank'>" + newLemma + "</a></li>");
                }
            });
            addLexemeField.val("");
            addLexemeField.focus();
        }
    })


    function createButton(type, text) {
        return $("<button type='button' class='btn \
            btn-" + type + "'>" + text + "</button>")
    }


    $('.add-sense-button').click(function() {
        var lid = $(this).attr('data-lid');
        var lang = $(this).attr('data-lang');
        var language = $(this).attr('data-language');
        var addSenseButton = $(this)
        var thisForm = $(this).parent('form');
        var cancelButton = createButton("secondary", "Cancel")
        cancelButton.attr('id', 'cancel-adding-button');
        cancelButton.click(function() {
            $(".addSenseField").remove();
            $(this).remove();
            infoMessage.remove();
            addSenseButton.html('Add a sense!');
        })
        var infoMessage = createAlert("info", "Add a sense in <strong> " + language + "</strong>.")
        thisForm.append(infoMessage)
        if ($(".addSenseField").length === 0) {
            var senseInput = createSenseInput()
            senseInput.insertBefore($(this));
            senseInput.focus()
            cancelButton.insertBefore($(this))
            $(this).html('Save')
        } else if ($(".addSenseField").length === 1 && $(".addSenseField").val().length > 1) {
            var content = $(".addSenseField").val();
            $(".addSenseField").prop('disabled', true);
            addSenseButton.html('Add a sense!');
            $("#cancel-adding-button").remove();
            $(".alert").remove();
            $.ajax({
                url: $SCRIPT_ROOT + '/edit/' + lid,
                dataType: 'json',
                type: 'post',
                contentType: 'application/json',
                data: JSON.stringify({
                    "what": "sense",
                    "lang": lang,
                    "content": content,
                    "lid": lid,
                    "token": getToken($(this))
                }),
                success: function(data) {
                    if (data["Status"] == "OK") {
                        var message = "<strong>Your edit was successful.</strong><br> \
                        <strong>Added: </strong><em>" + content + "</em><br>\
                        It might take a couple seconds before the \
                        changes in Wikidata are reflected here."
                        var successMessage = createAlert("success", message);
                        thisForm.prepend(successMessage);
                        $(".addSenseField").remove();
                    }

                }
            });




        }

    })
});