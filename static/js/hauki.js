$(document).ready(function() {

    function runLocally() {
        if (location.hostname == "localhost" || location.hostname == "127.0.0.1") {
            return true
        } else {
            return false
        }
    }

    function getSelectedLanguage() {
        return $("#language-selector option:selected").attr('data-code')
    }

    function getSearchQuery() {
        return $("#lexeme-searchbox").val()
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
});