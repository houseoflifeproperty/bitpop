(function($) {

    /*
     * Auto-growing textareas; technique ripped from Facebook
     */
    $.fn.autogrow = function(options) {
        
        this.filter('textarea').each(function() {
            
            var $this       = $(this),
                minHeight   = $this.height(),
                lineHeight  = $this.css('lineHeight');
            
            var shadow = $('<div></div>').css({
                position:   'absolute',
                top:        -10000,
                left:       -10000,
                width:      $(this).width(),
                fontSize:   $this.css('fontSize'),
                fontStyle:  $this.css('fontStyle'),
                fontWeight: $this.css('fontWeight'),
                fontFamily: $this.css('fontFamily'),
                lineHeight: $this.css('lineHeight'),
                wordWrap:   $this.css('wordWrap'),
                resize:     'none',
                textIndent: $this.css('textIndent')
            }).appendTo(document.body);
            
            var update = function() {
                
                var val = this.value.replace(/</g, '&lt;')
                                    .replace(/>/g, '&gt;')
                                    .replace(/&/g, '&amp;')
                                    .replace(/\n/g, '<br/>');
                
                shadow.html(val + '...');
                var prevHeight = $(this).height();
                var curHeight = Math.max(shadow.height(), minHeight);
                $(this).css('height', curHeight);
                
                if (prevHeight != curHeight)
                    $(this).trigger('height_should_change');

                if (!$(this).data('update_func'))
                    $(this).data('update_func', _.bind(arguments.callee, this));
            };
            
            $(this).change(update).keyup(update).keydown(update);
            
            update.apply(this);
            
        });
        
        return this;
        
    };
    
})(jQuery);
