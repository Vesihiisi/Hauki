$(document).ready(function() {

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
            url: '/autocomplete',
            wildcard: '*',
            limit: 20,
            prepare: function(query, settings) {
                settings.url += '?query=' + query + "&lang=" + getSelectedLanguage();
                return settings;
            },
            transform: function(response) {
                console.log(response)
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

    $("#lexeme-searchbox").keypress(function(e){
        console.log($(this).val())
        if(e.which == 13 && $(this).val()){
            $('#search-button').click();
        }
    });

    $('#lexeme-searchbox').on('typeahead:selected', function(evt, item) {
        executeSearch()
    })
});
