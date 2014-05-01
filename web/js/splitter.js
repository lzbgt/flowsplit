function Splitter (){
	var self = this;
	
	self.load = function load() {
		$.ajax({
			  url: '/data/stats',
			  cache: false,
			  async   : true,
			  success: function(data) {
					self.ondata(data);
			  }
		});
	}
	function addRow(tab, txt, val) {
		var row = $('<tr></tr>');
		tab.append(row);
		addCell(row, txt);
		addCell(row, val);
		return row;
	}	
    function addCell(row, cll, cls) {
		var cell = $('<td/>');
		row.append(cell);
		cell.append(cll);
		if(!(typeof(cls)==='undefined')){
			cell.addClass(cls);
		}
		return cell;
	}
    function addNum(row, cll) {
    	return addCell(row, cll, 'tbnum');
	}
    function addHead(row, cl) {
		var cell = $('<th/>');
		row.append(cell);
		cell.append(cl);
		return cell;
	}
    function mktable(nm, fields) {
		var tab = $('<table/>');
		var cap = $('<caption>');
		cap.append(nm);
		tab.append(cap);
		var head = $('<tr/>');
		tab.append(head);
		for ( var idx in fields) {
			var fdnm = fields[idx];
			addHead(head, fdnm);
		}
		return tab;
    }
    function addinput(tab, nm, dt) {
		var row = $('<tr></tr>');
		tab.append(row);
		addCell(row, nm);
		addNum(row, dt.all)
		addNum(row, dt.broken)
		addNum(row, dt.dropped)
	}
    function mktxt(txt, cls) {
    	var dv = $('<div>');
    	dv.append(txt);
    	dv.addClass(cls);
		return dv;
	}
    function whileago(val, nm) {
    	var v = Math.round(val);
    	if(v != 1) nm += 's';
    	return v.toString()+' '+nm+' ago';
	}
    function addtime(tab, nm, title, tm, now) {
		var row = $('<tr></tr>');
		tab.append(row);
		var cell = addCell(row, nm, 'tmname');
		if (title) row.attr('title', title);
		if (tm) {
			var d = new Date(tm);
			var seconds = (now - d)/1000;
			var when = '';
			if (seconds < 0) {
				when = 'future'
			} else if (seconds < 2) {
				when = 'now'
			} else if (seconds < 2*60) {
				when = whileago(seconds, 'second');
			} else if (seconds < 2*60*60) {
				when = whileago(seconds/60, 'minute');
			} else if (seconds < 2*60*60*24) {
				when = whileago(seconds/3600, 'hour')
			} else {
				when = whileago(seconds/3600/24, 'day')
			}
			addCell(row, mktxt(d.toLocaleDateString()+' '+d.toLocaleTimeString(), 'tmcls')).append(mktxt(when, 'reltmcls'));
		} else {
			addCell(row, '');
		}
	}

    var seldst = null;

    function scalevalue(mx, b){
    	if(mx > Math.pow(2, 50)){
    		return {'post':', T'+b, 'scale':Math.pow(2, 40)};
    	}    	
    	if(mx > Math.pow(2, 40)){
    		return {'post':', G'+b, 'scale':Math.pow(2, 30)};
    	}
    	if(mx > Math.pow(2, 30)){
    		return {'post':', M'+b, 'scale':Math.pow(2, 20)};
    	}
    	if(mx > Math.pow(2, 20)){
    		return {'post':', K'+b, 'scale':Math.pow(2, 10)};
    	}
    	if(b){
    		return {'post':', '+b, 'scale':1};
    	}
    	return {'post':'', 'scale':1};
    }
    
    function addLargeNum(row, scale, count) {
    	var cell = addNum(row, (scale == 1)? count : (count/scale).toFixed(1));
    	cell.attr('title', count);
    }
    
    function onmarks(data) {
        var mskcont = $('#mskcont');
        mskcont.empty();
        var mxpackets = 0, mxoctets = 0;
		for ( var idx = 0; idx < data.stats.length; idx++) {
			var stat = data.stats[idx];
			var st = stat[2];
			if (mxpackets < st.packets) mxpackets = st.packets;
			if (mxoctets < st.octets) mxoctets = st.octets;
		}
		var pktscale = scalevalue(mxpackets, '');
		var octscale = scalevalue(mxoctets, 'B');
		var tab = mktable(data.name, ['Subnet', 'flow pkts', 'flows', 'packets'+pktscale.post, 'octets'+octscale.post])
		mskcont.append(tab);
		for ( var idx = 0; idx < data.stats.length; idx++) {
			var stat = data.stats[idx];
			var st = stat[2];
			var row = $('<tr></tr>');
			tab.append(row);
			addCell(row, st.name);
			addNum(row, st.flowpackets);
			addNum(row, st.flows);
			addLargeNum(row, pktscale.scale, st.packets);
			addLargeNum(row, octscale.scale, st.octets);
		}
	}
    function ondest(ev) {
    	if(seldst){
    		seldst.removeClass('seldst');
    	}
    	seldst = $(ev.currentTarget);
    	seldst.addClass('seldst');
		var destname = $(ev.currentTarget.firstChild).text();
		$.ajax({
			  url: '/data/dest?name='+destname,
			  cache: false,
			  async   : true,
			  success: function(data) {
				  onmarks(data);
			  }
		});
	}
    
	self.ondata = function ondata(data) {
		var tmcont = $('#timecont');
		var tab = $('<table/>');
		tmcont.append(tab);
		var now = new Date();
		addtime(tab, 'Started', 'Application startup time', data.time.start, now);
		addtime(tab, 'Poll', 'Last sources check', data.time.poll, now);
		addtime(tab, 'Update', 'Last mapping config update from DB', data.time.dbpoll, now);
		
		var inpcont = $('#inpcont');
		var tab = mktable('Received Flow Packets', ['', 'all', 'broken', 'dropped'])
		inpcont.append(tab);
		addinput(tab, 'total', data.flows.total);
		addinput(tab, 'current', data.flows.current);

		var srccont = $('#srccont');
		var tab = mktable('Sources', ['address', 'total', 'bad seq', 'activity', 'state'])
		srccont.append(tab);
		for ( var idx in data.sources) {
			var src = data.sources[idx];
			var row = $('<tr></tr>');
			tab.append(row);
			addCell(row, src.address);
			addNum(row, src.total);
			var cell = addNum(row, src.ooscount);
			cell.attr('title', src.sequence);
			addNum(row, src.activity);
			addCell(row, (src.active == true)?mktxt('active', 'actvcls'):mktxt('inactive', 'inactcls'));
		}

		var dstcont = $('#dstcont');
        var mxpackets = 0, mxoctets = 0;
        for ( var idx in data.destinations) {
			var dst = data.destinations[idx];
			if (mxpackets < dst.stats.packets) mxpackets = dst.stats.packets;
			if (mxoctets < dst.stats.octets) mxoctets = dst.stats.octets;
		}
		var pktscale = scalevalue(mxpackets, '');
		var octscale = scalevalue(mxoctets, 'B');
		var tab = mktable('Destinations', ['address', 'flow pkts', 'flows', 'packets'+pktscale.post, 'octets'+octscale.post])
		dstcont.append(tab);
		for ( var idx in data.destinations) {
			var dst = data.destinations[idx];
			var row = $('<tr></tr>');
			row.addClass('dstrow');
			tab.append(row);
			addCell(row, dst.address);
			addNum(row, dst.stats.flowpackets);
			addNum(row, dst.stats.flows);
			addLargeNum(row, pktscale.scale, dst.stats.packets);
			addLargeNum(row, octscale.scale, dst.stats.octets);
			row.click(ondest);
		}
	}
}

var splitter = new Splitter();