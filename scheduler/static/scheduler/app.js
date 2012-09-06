/* CourseMate front end (jQuery 1.7) */
(function ($) {
  'use strict';

  var DAYS = ['M', 'T', 'W', 'R', 'F'];
  var DAY_NAMES = { M: 'Mon', T: 'Tue', W: 'Wed', R: 'Thu', F: 'Fri' };
  var START_HOUR = 7, END_HOUR = 21, PX_PER_MIN = 0.8;
  var COLORS = ['#e3f2fd', '#fce4ec', '#e8f5e9', '#fff3e0', '#ede7f6', '#e0f7fa', '#f9fbe7', '#efebe9'];

  var selected = [];
  var schedules = [];
  var current = 0;

  function esc(s) { return $('<div/>').text(s).html(); }
  function toMin(hhmm) { var p = hhmm.split(':'); return +p[0] * 60 + +p[1]; }

  function csrf() { return $('#prefs input[name=csrfmiddlewaretoken]').val(); }

  // --- course search ---
  var timer;
  $('#course-q').on('keyup', function () {
    var q = $.trim($(this).val());
    clearTimeout(timer);
    timer = setTimeout(function () {
      $.getJSON('/api/courses', { q: q }, function (data) {
        $('#course-results').html($.map(data.results, function (c) {
          var disabled = $.inArray(c.code, selected) >= 0 ? ' class="added"' : '';
          return '<li' + disabled + ' data-code="' + esc(c.code) + '"><strong>' + esc(c.code) + '</strong> ' +
            esc(c.title) + ' <span class="muted">' + c.sections + ' sections</span></li>';
        }).join(''));
      });
    }, 200);
  }).trigger('keyup');

  $('#course-results').on('click', 'li', function () {
    var code = $(this).data('code');
    if ($.inArray(code, selected) < 0) { selected.push(code); renderSelected(); }
    $(this).addClass('added');
  });

  $('#selected').on('click', '.remove', function () {
    var code = $(this).parent().data('code');
    selected = $.grep(selected, function (c) { return c !== code; });
    renderSelected();
    $('#course-results li[data-code="' + code + '"]').removeClass('added');
  });

  function renderSelected() {
    $('#selected').html($.map(selected, function (code) {
      return '<li data-code="' + esc(code) + '">' + esc(code) + ' <a href="#" class="remove">&times;</a></li>';
    }).join('') || '<li class="muted">None yet</li>');
  }
  renderSelected();

  // --- generation ---
  $('#prefs').on('submit', function (e) {
    e.preventDefault();
    if (!selected.length) { showMessage('Add at least one course first.'); return; }
    var payload = {
      courses: selected,
      earliest: this.earliest.value,
      latest: this.latest.value,
      daysOff: $('input[name=daysOff]:checked').map(function () { return this.value; }).get(),
      includeFull: this.includeFull.checked
    };
    $.ajax({
      url: '/api/schedules', type: 'POST', contentType: 'application/json', dataType: 'json',
      data: JSON.stringify(payload), headers: { 'X-CSRFToken': csrf() }
    }).done(function (data) {
      schedules = data.schedules;
      current = 0;
      $('#summary').text(data.count + ' found' + (data.truncated ? ' (search limit reached)' : ''));
      if (data.unsatisfiable.length) {
        showMessage('No section of ' + data.unsatisfiable.join(', ') + ' fits your preferences.');
      } else if (!schedules.length) {
        var pairs = $.map(data.conflicts || [], function (p) { return p[0] + ' & ' + p[1]; });
        showMessage('No conflict-free combination.' + (pairs.length ? ' Always clashing: ' + pairs.join('; ') : ''));
      } else {
        showMessage('');
      }
      render();
    }).fail(function (xhr) {
      showMessage((xhr.responseJSON || $.parseJSON(xhr.responseText || '{}')).error || 'Request failed');
    });
  });

  $('#prev').on('click', function () { if (current > 0) { current--; render(); } });
  $('#next').on('click', function () { if (current < schedules.length - 1) { current++; render(); } });
  $(document).on('keydown', function (e) {
    if (e.target.tagName === 'INPUT') { return; }
    if (e.which === 37) { $('#prev').click(); }
    if (e.which === 39) { $('#next').click(); }
  });

  function showMessage(text) { $('#message').text(text).toggle(!!text); }

  function render() {
    var $cal = $('#calendar').empty();
    $('#nav').prop('hidden', schedules.length < 2);
    if (!schedules.length) { return; }
    var s = schedules[current];
    $('#position').text((current + 1) + ' / ' + schedules.length + ' — ' + s.daysOnCampus + ' days, ' +
      s.gapMinutes + ' min between classes');

    var height = (END_HOUR - START_HOUR) * 60 * PX_PER_MIN;
    var $hours = $('<div class="hours"/>').css('height', height);
    for (var h = START_HOUR; h < END_HOUR; h++) {
      $hours.append($('<div class="hour"/>').css('top', (h - START_HOUR) * 60 * PX_PER_MIN)
        .text((h % 12 || 12) + (h < 12 ? 'a' : 'p')));
    }
    $cal.append($hours);

    $.each(DAYS, function (_, day) {
      var $col = $('<div class="day"/>').css('height', height).append('<div class="day-name">' + DAY_NAMES[day] + '</div>');
      $.each(s.sections, function (i, sec) {
        $.each(sec.meetings, function (_, m) {
          if (m.day !== day) { return; }
          var top = (toMin(m.start) - START_HOUR * 60) * PX_PER_MIN;
          var h = (toMin(m.end) - toMin(m.start)) * PX_PER_MIN;
          $col.append($('<div class="block"/>').css({ top: top, height: h, background: COLORS[i % COLORS.length] })
            .html('<strong>' + esc(sec.course) + '</strong><br>' + m.start + '–' + m.end +
              '<br><span class="muted">CRN ' + esc(sec.crn) + (sec.full ? ' · FULL' : '') + '</span>'));
        });
      });
      $cal.append($col);
    });
  }
})(jQuery);
