// Benchmark "benchmark/s26/s26_G17" written by ABC on Fri Sep 24 13:30:38 2021

module \benchmark/s26/s26_G17  ( 
    G0, G1, G2, G5, G6,
    G17  );
  input  G0, G1, G2, G5, G6;
  output G17;
  wire new_n7_, new_n8_, new_n9_, new_n10_, new_n11_, new_n12_, new_n13_;
  assign new_n7_ = ~G0;
  assign new_n8_ = new_n7_ & G6;
  assign new_n9_ = G2 | new_n8_;
  assign new_n10_ = ~G1 & ~G6;
  assign new_n11_ = new_n10_ | new_n8_;
  assign new_n12_ = ~new_n9_ | ~new_n11_;
  assign new_n13_ = ~G5 & ~new_n12_;
  assign G17 = ~new_n13_;
endmodule


